import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.graph.solve_graph import solve_graph
from app.graph.followup_graph import followup_graph
from app.graph.nodes.deep_evaluate import run_deep_evaluate
from app.models.scan_record import ScanRecord
from app.models.solution import Solution
from app.schemas.scan import ScanResponse, SolutionResponse, SolutionStep
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

storage_service = StorageService()


class ScanService:
    """Service for handling problem scanning and solving via LangGraph."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._graph = solve_graph
        self._followup_graph = followup_graph
        self._conversation_service = ConversationService(db)
        self._embedding_service = EmbeddingService(db)

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
        image_url: Optional[str] = None
        image_bytes: Optional[bytes] = None

        if image:
            # Image flow: upload and read bytes for OCR
            image_url = await storage_service.upload_image(image)
            image.file.seek(0)
            image_bytes = await image.read()

        # 3. Run the LangGraph pipeline
        result = await self._graph.ainvoke({
            "image_bytes": image_bytes,
            "image_url": image_url,
            "input_text": text,
            "user_id": user_id,
            "subject": subject,
            "grade_level": grade_level,
            "preferred_provider": ai_provider,
            "attempt_count": 0,
        })

        # 4. Persist scan record
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

        # 5. Compute verification status from quick_verify results
        final = result.get("final_solution", {})
        verify_passed = result.get("verify_passed")
        verify_confidence = result.get("verify_confidence", 0.0)

        if verify_passed is True and verify_confidence >= 0.8:
            verification_status = "verified"
        elif verify_passed is False and result.get("attempt_count", 0) >= 2:
            verification_status = "caution"
        else:
            verification_status = "unverified"

        # 6. Persist solution
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

        # 6. Save initial conversation messages
        await self._conversation_service.add_message(
            scan_record.id, "system",
            f"Problem: {result.get('ocr_text', '')}",
        )
        # Build a readable summary instead of storing the raw JSON
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
        assistant_summary = "\n".join(summary_parts) if summary_parts else result.get("solution_raw", "")
        await self._conversation_service.add_message(
            scan_record.id, "assistant",
            assistant_summary,
        )

        await self.db.commit()

        # 7. Generate embedding (best-effort, non-blocking)
        try:
            await self._embedding_service.embed_scan_record(
                scan_record.id, result.get("ocr_text", "")
            )
            await self.db.commit()
        except Exception:
            pass

        # 8. Fire async deep evaluation (non-blocking)
        asyncio.create_task(
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

        # 9. Build response
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
