"""Service for generating practice questions from a solved scan."""

import json
import logging
import re
from typing import Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.prompts.generate_practice import build_generate_practice_messages
from app.llm.registry import get_llm
from app.models.exam_paper import PracticeQuestion
from app.models.scan_record import ScanRecord

logger = logging.getLogger(__name__)


class PracticeGenerationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_generate(
        self,
        scan_id: int,
        user_id: int,
        force_refresh: bool = False,
    ) -> list[PracticeQuestion]:
        """Get existing practice questions or generate new ones."""
        if not force_refresh:
            existing = await self._get_existing(scan_id, user_id)
            if existing:
                return existing

        # Check refresh limit (max 3 refreshes = 12 total questions)
        total = await self._count_existing(scan_id, user_id)
        if total >= 12:
            return await self._get_existing(scan_id, user_id)

        return await self._generate(scan_id, user_id)

    async def _get_existing(
        self, scan_id: int, user_id: int
    ) -> list[PracticeQuestion]:
        """Fetch existing generated questions for this scan+user."""
        result = await self.db.execute(
            select(PracticeQuestion)
            .where(
                PracticeQuestion.source_scan_id == scan_id,
                PracticeQuestion.generated_for_user_id == user_id,
                PracticeQuestion.source == "ai_generated",
            )
            .order_by(PracticeQuestion.created_at.desc())
            .limit(3)
        )
        return list(result.scalars().all())

    async def _count_existing(self, scan_id: int, user_id: int) -> int:
        result = await self.db.execute(
            select(sa_func.count(PracticeQuestion.id)).where(
                PracticeQuestion.source_scan_id == scan_id,
                PracticeQuestion.generated_for_user_id == user_id,
                PracticeQuestion.source == "ai_generated",
            )
        )
        return result.scalar() or 0

    async def _generate(
        self, scan_id: int, user_id: int
    ) -> list[PracticeQuestion]:
        """Generate 3 practice questions from a scan's solution."""
        scan = await self._load_scan(scan_id)
        if not scan or not scan.solutions:
            raise ValueError(f"Scan {scan_id} not found or has no solution")

        solution = scan.solutions[0]

        steps = solution.steps or []
        steps_summary = " -> ".join(
            s.get("description", "") for s in steps[:5]
        ) if steps else "No steps available"

        messages = build_generate_practice_messages(
            ocr_text=scan.ocr_text or "",
            subject=scan.subject or "math",
            difficulty=scan.difficulty or "medium",
            problem_type=scan.problem_type or "general",
            knowledge_points=scan.knowledge_points or [],
            solution_steps_summary=steps_summary,
            grade_level="high school",
        )

        provider = solution.ai_provider or "gemini"
        llm = get_llm(tier="strong", provider=provider)

        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
        except Exception:
            logger.exception("Practice generation LLM call failed, trying gemini")
            llm = get_llm(tier="strong", provider="gemini")
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

        questions_data = self._parse_response(content)

        saved = []
        for q_data in questions_data:
            question = PracticeQuestion(
                exam_paper_id=None,
                question_number=f"G{q_data.get('difficulty_offset', 0) + 1}",
                sub_question="",
                question_text=q_data.get("question_text", ""),
                question_type=q_data.get("question_type", "numeric"),
                correct_answer=q_data.get("correct_answer"),
                accepted_answers=q_data.get("accepted_answers", []),
                answer_explanation=q_data.get("answer_explanation"),
                marks=str(q_data.get("marks", 3)),
                options=q_data.get("options"),
                has_image=False,
                order_index=q_data.get("difficulty_offset", 0),
                source="ai_generated",
                status="approved",
                source_scan_id=scan_id,
                generated_for_user_id=user_id,
                visibility="private",
                difficulty_offset=q_data.get("difficulty_offset", 0),
                knowledge_points=q_data.get("knowledge_points", []),
                problem_type_tag=q_data.get("question_type", scan.problem_type),
                difficulty=q_data.get("difficulty", scan.difficulty),
            )
            self.db.add(question)
            saved.append(question)

        await self.db.commit()
        for q in saved:
            await self.db.refresh(q)
        return saved

    async def _load_scan(self, scan_id: int) -> Optional[ScanRecord]:
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(ScanRecord)
            .options(selectinload(ScanRecord.solutions))
            .where(ScanRecord.id == scan_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _parse_response(content: str) -> list[dict]:
        """Parse LLM JSON response into list of question dicts."""
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in generation response")

        data = json.loads(json_match.group())
        questions = data.get("questions", [])

        if not questions or len(questions) < 1:
            raise ValueError("No questions in generation response")

        validated = []
        for q in questions[:3]:
            if not q.get("question_text"):
                continue
            validated.append(q)

        if not validated:
            raise ValueError("No valid questions parsed from response")

        return validated
