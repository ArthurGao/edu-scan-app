"""Per-question grading for practice answers — exact match + AI with cache."""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.registry import get_llm
from app.models.exam_paper import PracticeQuestion
from app.models.grading_cache import GradingCache
from app.models.practice_answer import PracticeAnswer
from app.schemas.practice import SubmitAnswerResponse

logger = logging.getLogger(__name__)

GRADE_SINGLE_SYSTEM = """You are grading a student's answer to a {subject} question.
Respond ONLY in valid JSON format."""

GRADE_SINGLE_USER = """## Question
{question_text}

## Correct Answer
{correct_answer}

## Answer Explanation
{answer_explanation}

## Student's Answer
{student_answer}

Evaluate whether the student's answer is correct.
- Be lenient on formatting: "x = 2", "2", "x=2" are all acceptable for numeric answers.
- For partial credit: if the core idea is right but details wrong, mark as incorrect but give encouraging feedback.

Respond in JSON:
{{
  "is_correct": true or false,
  "feedback": "Explanation of why the answer is correct/incorrect"
}}"""


class PracticeGradingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @traceable(run_type="chain", name="grading.practice", tags=["grading", "practice"])
    async def grade_and_save(
        self,
        question: PracticeQuestion,
        user_id: int,
        student_answer: str,
        time_spent_seconds: Optional[int] = None,
    ) -> SubmitAnswerResponse:
        """Grade a single practice answer and persist result."""
        if question.question_type in ("numeric", "multichoice"):
            is_correct, feedback = self._exact_match(question, student_answer)
            grading_method = "exact_match"
            ai_feedback = None
        else:
            is_correct, feedback, ai_feedback = await self._ai_grade_with_cache(
                question, student_answer
            )
            grading_method = "ai_grading"

        answer = PracticeAnswer(
            user_id=user_id,
            question_id=question.id,
            student_answer=student_answer,
            is_correct=is_correct,
            grading_method=grading_method,
            ai_feedback=ai_feedback or feedback,
            time_spent_seconds=time_spent_seconds,
        )
        self.db.add(answer)

        await self._update_stats(question, is_correct)
        await self.db.commit()

        return SubmitAnswerResponse(
            is_correct=is_correct,
            grading_method=grading_method,
            correct_answer=question.correct_answer,
            accepted_answers=question.accepted_answers,
            answer_explanation=question.answer_explanation,
            ai_feedback=ai_feedback or feedback,
            knowledge_points=question.knowledge_points,
        )

    def _exact_match(
        self, question: PracticeQuestion, student_answer: str
    ) -> tuple[bool, str]:
        """Grade via exact match for numeric/multichoice."""
        student = student_answer.strip()
        if not student:
            return False, "No answer provided."

        correct = (question.correct_answer or "").strip()
        accepted = question.accepted_answers or []

        if question.question_type == "multichoice":
            normalised = student.upper()
            all_accepted = [correct.upper()] + [a.upper() for a in accepted]
            is_correct = normalised in all_accepted
        else:
            normalised = self._normalize_numeric(student)
            all_accepted = [self._normalize_numeric(correct)] + [
                self._normalize_numeric(a) for a in accepted
            ]
            is_correct = normalised in all_accepted

        feedback = "Correct!" if is_correct else f"Incorrect. Expected: {correct}"
        return is_correct, feedback

    async def _ai_grade_with_cache(
        self, question: PracticeQuestion, student_answer: str
    ) -> tuple[bool, str, Optional[str]]:
        """AI grading with cache lookup."""
        answer_hash = hashlib.sha256(
            student_answer.strip().lower().encode()
        ).hexdigest()

        result = await self.db.execute(
            select(GradingCache).where(
                GradingCache.question_id == question.id,
                GradingCache.answer_hash == answer_hash,
            )
        )
        cached = result.scalar_one_or_none()
        if cached:
            return cached.is_correct, "", cached.feedback

        subject = "general"
        if question.knowledge_points:
            subject = question.knowledge_points[0] if question.knowledge_points else "general"

        lc_messages = [
            SystemMessage(content=GRADE_SINGLE_SYSTEM.format(subject=subject)),
            HumanMessage(content=GRADE_SINGLE_USER.format(
                question_text=question.question_text,
                correct_answer=question.correct_answer or "",
                answer_explanation=question.answer_explanation or "N/A",
                student_answer=student_answer,
            )),
        ]

        try:
            llm = get_llm(tier="fast", provider="gemini")
            response = await llm.ainvoke(lc_messages)
            content = response.content if hasattr(response, "content") else str(response)

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON in AI grading response")

            data = json.loads(json_match.group())
            is_correct = bool(data.get("is_correct", False))
            ai_feedback = data.get("feedback", "")

            cache_entry = GradingCache(
                question_id=question.id,
                answer_hash=answer_hash,
                is_correct=is_correct,
                feedback=ai_feedback,
            )
            self.db.add(cache_entry)

            return is_correct, "", ai_feedback

        except Exception:
            logger.exception("AI grading failed for question %d", question.id)
            return False, "AI grading failed. Please try again.", None

    async def _update_stats(
        self, question: PracticeQuestion, is_correct: bool
    ) -> None:
        """Update usage_count and correct_rate, check auto-promote."""
        question.usage_count = (question.usage_count or 0) + 1

        if question.correct_rate is None:
            question.correct_rate = 1.0 if is_correct else 0.0
        else:
            question.correct_rate += (
                (1.0 if is_correct else 0.0) - question.correct_rate
            ) / question.usage_count

        if (
            question.source == "ai_generated"
            and question.visibility == "private"
            and question.usage_count >= 10
            and question.correct_rate is not None
            and 0.3 <= question.correct_rate <= 0.9
        ):
            question.visibility = "public"
            question.auto_promoted_at = datetime.now(timezone.utc)
            logger.info(
                "Auto-promoted question %d to public (usage=%d, rate=%.2f)",
                question.id, question.usage_count, question.correct_rate,
            )

    @staticmethod
    def _normalize_numeric(value: str) -> str:
        """Normalize numeric answer for comparison."""
        value = value.strip().lower()
        for prefix in ("x=", "x =", "y=", "y ="):
            if value.startswith(prefix):
                value = value[len(prefix):].strip()
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        if "." in value:
            int_part, dec_part = value.split(".", 1)
            int_part = int_part.lstrip("0") or "0"
            value = f"{int_part}.{dec_part}"
        else:
            value = value.lstrip("0") or "0"
        if "/" in value:
            parts = value.split("/")
            try:
                result = float(parts[0]) / float(parts[1])
                value = str(result).rstrip("0").rstrip(".")
            except (ValueError, ZeroDivisionError):
                pass
        return value
