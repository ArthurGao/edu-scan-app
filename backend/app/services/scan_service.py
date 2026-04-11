import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Optional

from fastapi import UploadFile
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.graph.solve_graph import solve_graph
from app.graph.followup_graph import followup_graph
from app.graph.nodes.deep_evaluate import run_deep_evaluate
from app.llm.embeddings import embed_text
from app.llm.prompts.framework import build_framework_messages
from app.llm.registry import get_llm
from app.observability.tracing import spawn_in_current_context
from app.models.scan_record import ScanRecord
from app.models.semantic_cache import SemanticCache
from app.models.solution import Solution
from app.schemas.scan import ScanResponse, SolutionResponse, SolutionStep
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.storage_service import StorageService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

storage_service = StorageService()
_settings = get_settings()


def _input_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _tag_current_run(
    *,
    subject: Optional[str],
    user_tier: str,
    provider: Optional[str],
    user_id: int,
) -> None:
    """Attach business-dimension tags to the active LangSmith run, if any.

    Safe no-op when tracing is disabled (``get_current_run_tree`` returns None).
    Failures are swallowed — observability must never break user requests.
    """
    try:
        tree = get_current_run_tree()
    except Exception:
        return
    if tree is None:
        return
    try:
        tree.add_tags([
            f"subject:{subject or 'unknown'}",
            f"tier:{user_tier}",
            f"provider:{provider or 'default'}",
        ])
        tree.add_metadata({"user_id": user_id})
    except Exception:
        pass


class ScanService:
    """Service for handling problem scanning and solving via LangGraph."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._graph = solve_graph
        self._followup_graph = followup_graph
        self._conversation_service = ConversationService(db)
        self._embedding_service = EmbeddingService(db)

    @traceable(run_type="chain", name="scan.solve", tags=["scan"])
    async def scan_and_solve(
        self,
        user_id: int,
        image: Optional[UploadFile] = None,
        text: Optional[str] = None,
        subject: Optional[str] = None,
        ai_provider: Optional[str] = None,
        grade_level: Optional[str] = None,
    ) -> ScanResponse:
        """Process uploaded image or typed text through LangGraph pipeline."""
        # -- Tier check: usage limit gate --
        sub_service = SubscriptionService(self.db)
        user_tier = await sub_service.get_user_tier(user_id)
        if user_tier == "free":
            allowed, remaining = await sub_service.check_usage_limit(user_id)
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={"error": "daily_limit_exceeded", "remaining": 0},
                )

        _tag_current_run(
            subject=subject, user_tier=user_tier,
            provider=ai_provider, user_id=user_id,
        )

        image_url: Optional[str] = None
        image_bytes: Optional[bytes] = None

        if image:
            # Image flow: upload and read bytes for OCR
            image_url = await storage_service.upload_image(image)
            image.file.seek(0)
            image_bytes = await image.read()

        # Run the LangGraph pipeline
        result = await self._graph.ainvoke({
            "image_bytes": image_bytes,
            "image_url": image_url,
            "input_text": text,
            "user_id": user_id,
            "subject": subject,
            "grade_level": grade_level,
            "preferred_provider": ai_provider,
            "user_tier": user_tier,
            "attempt_count": 0,
        })

        response = await self._persist_and_build_response(
            result, user_id, image_url, grade_level
        )

        # -- Increment usage after successful solve --
        await sub_service.increment_usage(user_id)

        return response

    # -- Node-name → user-facing stage messages --------------------------
    _NODE_STAGES: dict[str, str] = {
        "ocr": "Extracting text from image...",
        "analyze": "Analyzing problem...",
        "retrieve": "Searching knowledge base...",
        "solve": "Generating solution...",
        "quick_verify": "Verifying answer...",
        "enrich": "Enriching solution...",
    }

    @traceable(run_type="chain", name="scan.solve.stream", tags=["scan", "stream"])
    async def scan_and_solve_stream(
        self,
        user_id: int,
        image: Optional[UploadFile] = None,
        text: Optional[str] = None,
        subject: Optional[str] = None,
        ai_provider: Optional[str] = None,
        grade_level: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream the solve pipeline, yielding SSE-ready dicts per node."""
        # -- Tier check: usage limit gate --
        sub_service = SubscriptionService(self.db)
        user_tier = await sub_service.get_user_tier(user_id)
        if user_tier == "free":
            allowed, remaining = await sub_service.check_usage_limit(user_id)
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={"error": "daily_limit_exceeded", "remaining": 0},
                )

        _tag_current_run(
            subject=subject, user_tier=user_tier,
            provider=ai_provider, user_id=user_id,
        )

        image_url: Optional[str] = None
        image_bytes: Optional[bytes] = None

        if image:
            image_url = await storage_service.upload_image(image)
            image.file.seek(0)
            image_bytes = await image.read()

        initial_input = {
            "image_bytes": image_bytes,
            "image_url": image_url,
            "input_text": text,
            "user_id": user_id,
            "subject": subject,
            "grade_level": grade_level,
            "preferred_provider": ai_provider,
            "user_tier": user_tier,
            "attempt_count": 0,
        }

        accumulated: dict[str, Any] = {}

        try:
            async for chunk in self._graph.astream(
                initial_input, stream_mode="updates"
            ):
                for node_name, update in chunk.items():
                    accumulated.update(update)

                    if node_name in self._NODE_STAGES:
                        yield {
                            "event": "stage",
                            "data": {
                                "stage": node_name,
                                "message": self._NODE_STAGES[node_name],
                            },
                        }

                    if node_name == "ocr" and "ocr_text" in update:
                        yield {
                            "event": "ocr_result",
                            "data": {"ocr_text": update["ocr_text"]},
                        }

            # -- Pipeline complete — persist (mirrors scan_and_solve) -------
            result = accumulated
            response = await self._persist_and_build_response(
                result, user_id, image_url, grade_level
            )

            # -- Increment usage after successful solve --
            await sub_service.increment_usage(user_id)

            yield {
                "event": "complete",
                "data": response.model_dump(mode="json"),
            }

        except Exception as e:
            logger.exception("Streaming solve failed")
            yield {"event": "error", "data": {"message": str(e)}}

    # -- Shared persistence helper --------------------------------------

    async def _persist_and_build_response(
        self,
        result: dict[str, Any],
        user_id: int,
        image_url: Optional[str],
        grade_level: Optional[str],
    ) -> ScanResponse:
        """Persist scan record, solution, conversation and return response."""
        scan_record = ScanRecord(
            user_id=user_id,
            image_url=image_url,
            ocr_text=result.get("ocr_text", ""),
            ocr_confidence=result.get("ocr_confidence"),
            subject=result.get("detected_subject"),
            problem_type=result.get("problem_type"),
            difficulty=result.get("difficulty"),
            knowledge_points=result.get("knowledge_points", []),
        )
        self.db.add(scan_record)
        await self.db.flush()

        final = result.get("final_solution", {})
        verify_passed = result.get("verify_passed")
        verify_confidence = result.get("verify_confidence", 0.0)

        if verify_passed is True and verify_confidence >= 0.8:
            verification_status = "verified"
        elif verify_passed is False and result.get("attempt_count", 0) >= 2:
            verification_status = "caution"
        else:
            verification_status = "unverified"

        solution = Solution(
            scan_id=scan_record.id,
            ai_provider=result.get("llm_provider", "unknown"),
            model=result.get("llm_model", "unknown"),
            content=result.get("solution_raw", ""),
            steps=final.get("steps"),
            final_answer=final.get("final_answer"),
            knowledge_points=result.get("knowledge_points", []),
            quality_score=result.get("quality_score"),
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
            attempt_number=result.get("attempt_count", 1),
            related_formula_ids=result.get("related_formula_ids", []),
            verification_status=verification_status,
            verification_confidence=verify_confidence,
        )
        self.db.add(solution)

        await self._conversation_service.add_message(
            scan_record.id, "system",
            f"Problem: {result.get('ocr_text', '')}",
        )
        summary_parts = []
        if final.get("final_answer"):
            summary_parts.append(f"Answer: {final['final_answer']}")
        steps = final.get("steps") or []
        if steps:
            summary_parts.append("Steps:")
            for s in steps:
                step_num = s.get("step", "")
                desc = s.get("description", "")
                summary_parts.append(f"  {step_num}. {desc}")
        assistant_summary = (
            "\n".join(summary_parts) if summary_parts
            else result.get("solution_raw", "")
        )
        await self._conversation_service.add_message(
            scan_record.id, "assistant", assistant_summary,
        )

        await self.db.commit()

        try:
            await self._embedding_service.embed_scan_record(
                scan_record.id, result.get("ocr_text", "")
            )
            await self.db.commit()
        except Exception:
            pass

        # Layer 4 only: write solution to cache then generate framework
        cache_layer = result.get("cache_layer", 4)
        _LAYER_LABELS = {1: "L1-Redis(exact)", 2: "L2-pgvector(≥0.95)", 3: "L3-framework(0.80-0.95)", 4: "L4-full-solve"}
        logger.info(">>> CACHE RESULT: %s | scan_id=%s", _LAYER_LABELS.get(cache_layer, f"L{cache_layer}"), scan_record.id)

        # Only deep-evaluate fresh LLM solutions (not cache hits)
        if cache_layer == 4:
            spawn_in_current_context(
                self._run_deep_evaluate_background(
                    solution_id=solution.id,
                    problem_text=result.get("ocr_text", ""),
                    solution_raw=result.get("solution_raw", ""),
                    final_answer=final.get("final_answer", ""),
                    steps=final.get("steps", []),
                    subject=result.get("detected_subject", "math"),
                    grade_level=grade_level or "middle school",
                )
            )
        ocr_text = result.get("ocr_text", "")
        if cache_layer == 4 and ocr_text and final:
            spawn_in_current_context(
                self._write_to_cache(
                    ocr_text=ocr_text,
                    response=final,
                    model_used=result.get("llm_model", "unknown"),
                )
            )
            spawn_in_current_context(
                self._generate_framework_background(
                    ocr_text=ocr_text,
                    solution_raw=result.get("solution_raw", ""),
                    subject=result.get("detected_subject", "math"),
                )
            )
        # Generate practice questions in background
        if scan_record.user_id:
            spawn_in_current_context(
                self._generate_practice_background(
                    scan_id=scan_record.id,
                    user_id=scan_record.user_id,
                )
            )

        return ScanResponse(
            scan_id=str(scan_record.id),
            ocr_text=result.get("ocr_text", ""),
            solution=SolutionResponse(
                question_type=final.get("question_type", ""),
                knowledge_points=final.get("knowledge_points", []),
                steps=[SolutionStep(**s) for s in final.get("steps", [])],
                final_answer=final.get("final_answer", ""),
                explanation=final.get("explanation"),
                tips=final.get("tips"),
                verification_status=verification_status,
                verification_confidence=verify_confidence,
            ),
            related_formulas=[],
            created_at=scan_record.created_at or datetime.utcnow(),
        )

    async def _write_to_cache(self, ocr_text: str, response: dict, model_used: str) -> None:
        """Write a Layer 4 solution to Redis + semantic_cache (background-safe, own session)."""
        if not ocr_text:
            return
        cache_key = _input_hash(ocr_text)

        # Layer 1: Redis
        try:
            from redis.asyncio import from_url as redis_from_url
            redis = redis_from_url(_settings.redis_url, decode_responses=True)
            await redis.set(f"solve:{cache_key}", json.dumps(response))
            await redis.aclose()
        except Exception as e:
            logger.warning("Cache Redis write failed: %s", e)

        # Layer 2/3: semantic_cache
        try:
            embedding = await embed_text(ocr_text)
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            async with AsyncSessionLocal() as db:
                stmt = pg_insert(SemanticCache).values(
                    input_hash=cache_key,
                    input_text=ocr_text,
                    embedding=embedding,
                    response=response,
                    model_used=model_used,
                ).on_conflict_do_nothing(index_elements=["input_hash"])
                await db.execute(stmt)
                await db.commit()
        except Exception as e:
            logger.warning("Cache semantic_cache write failed: %s", e)

    async def _generate_framework_background(
        self, ocr_text: str, solution_raw: str, subject: str
    ) -> None:
        """Generate solution_framework via Haiku and store in semantic_cache (background)."""
        if not ocr_text or not solution_raw:
            return
        try:
            # Use fast model — framework generation doesn't need Sonnet
            llm = get_llm("fast")
            messages = build_framework_messages(ocr_text, solution_raw, subject)
            result = await llm.ainvoke(messages)

            try:
                framework = json.loads(result.content)
            except json.JSONDecodeError:
                content = result.content
                start, end = content.find("{"), content.rfind("}") + 1
                if start >= 0 and end > start:
                    framework = json.loads(content[start:end])
                else:
                    return  # Unparseable — skip

            cache_key = _input_hash(ocr_text)
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(SemanticCache)
                    .where(SemanticCache.input_hash == cache_key)
                    .values(solution_framework=framework)
                )
                await db.commit()
            logger.info("Framework generated for cache key %s…", cache_key[:8])
        except Exception as e:
            logger.warning("Background framework generation failed: %s", e)

    async def _run_deep_evaluate_background(
        self,
        solution_id: int,
        problem_text: str,
        solution_raw: str,
        final_answer: str,
        steps: list,
        subject: str,
        grade_level: str,
    ) -> None:
        """Run deep evaluation in the background and persist results."""
        try:
            evaluation = await run_deep_evaluate(
                problem_text=problem_text,
                solution_raw=solution_raw,
                final_answer=final_answer,
                steps=steps,
                subject=subject,
                grade_level=grade_level,
            )
            if evaluation:
                result = await self.db.execute(
                    select(Solution).where(Solution.id == solution_id)
                )
                sol = result.scalar_one_or_none()
                if sol:
                    sol.deep_evaluation = evaluation
                    sol.quality_score = evaluation.get("overall", sol.quality_score)
                    await self.db.commit()
                    logger.info("Deep evaluation saved for solution %s", solution_id)
        except Exception as e:
            logger.warning("Background deep_evaluate failed for solution %s: %s", solution_id, e)

    @traceable(run_type="chain", name="scan.followup", tags=["followup"])
    async def followup(
        self, scan_id: int, user_id: int, message: str
    ) -> dict:
        """Handle follow-up question on a scan."""
        history = await self._conversation_service.get_history(scan_id)

        # Get scan record for context
        result_row = await self.db.execute(
            select(ScanRecord).where(ScanRecord.id == scan_id)
        )
        scan_record = result_row.scalars().first()
        subject = scan_record.subject if scan_record else "math"

        # Run follow-up graph
        result = await self._followup_graph.ainvoke({
            "scan_id": scan_id,
            "user_message": message,
            "conversation_history": history,
            "subject": subject,
            "grade_level": "middle school",
        })

        # Save messages
        await self._conversation_service.add_message(scan_id, "user", message)
        await self._conversation_service.add_message(
            scan_id, "assistant", result.get("reply", "")
        )
        await self.db.commit()

        return {
            "reply": result.get("reply", ""),
            "tokens_used": result.get("tokens_used", 0),
        }

    async def get_scan_result(self, scan_id: int) -> Optional[ScanResponse]:
        """Retrieve a previous scan result."""
        result = await self.db.execute(
            select(ScanRecord)
            .options(selectinload(ScanRecord.solutions))
            .where(ScanRecord.id == scan_id)
        )
        scan_record = result.scalar_one_or_none()
        if not scan_record:
            return None

        solution = scan_record.solutions[0] if scan_record.solutions else None
        if not solution:
            return None

        steps = [SolutionStep(**s) for s in (solution.steps or [])]
        return ScanResponse(
            scan_id=str(scan_record.id),
            ocr_text=scan_record.ocr_text or "",
            solution=SolutionResponse(
                question_type=solution.knowledge_points[0] if solution.knowledge_points else "",
                knowledge_points=solution.knowledge_points or [],
                steps=steps,
                final_answer=solution.final_answer or "",
                explanation=solution.content,
                verification_status=solution.verification_status or "unverified",
                verification_confidence=solution.verification_confidence or 0.0,
            ),
            related_formulas=[],
            created_at=scan_record.created_at,
        )

    async def _generate_practice_background(
        self, scan_id: int, user_id: int
    ) -> None:
        """Background: generate practice questions after solve."""
        try:
            from app.database import AsyncSessionLocal
            from app.services.practice_generation_service import PracticeGenerationService

            async with AsyncSessionLocal() as db:
                service = PracticeGenerationService(db)
                await service.get_or_generate(scan_id=scan_id, user_id=user_id)
                logger.info("Background practice generation done for scan %d", scan_id)
        except Exception:
            logger.exception("Background practice generation failed for scan %d", scan_id)
