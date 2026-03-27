"""Service for grading exam session answers — programmatic + AI."""

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.llm.prompts.grading import build_grading_messages
from app.llm.registry import get_llm
from app.models.exam_paper import PracticeQuestion
from app.models.exam_session import ExamAnswer, ExamSession

logger = logging.getLogger(__name__)


class GradingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def grade_session(self, session_id: int) -> ExamSession:
        """Grade all answers in a session and update totals."""
        result = await self.db.execute(
            select(ExamSession)
            .options(
                selectinload(ExamSession.answers).selectinload(ExamAnswer.question)
            )
            .where(ExamSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"ExamSession {session_id} not found")

        # Separate answers by question type
        exact_match_answers: list[ExamAnswer] = []
        ai_answers: list[ExamAnswer] = []

        for answer in session.answers:
            q = answer.question
            if q.question_type in ("multichoice", "numeric"):
                exact_match_answers.append(answer)
            else:
                ai_answers.append(answer)

        # Grade exact-match questions programmatically
        for answer in exact_match_answers:
            self._grade_exact_match(answer, answer.question)

        # Grade explanation questions via AI in batches of 5
        if ai_answers:
            for i in range(0, len(ai_answers), 5):
                batch = ai_answers[i : i + 5]
                await self._grade_ai_batch(
                    [(a, a.question) for a in batch]
                )

        # Calculate totals
        total_score = 0.0
        max_score = 0.0
        for answer in session.answers:
            total_score += answer.score or 0.0
            max_score += answer.max_score or 1.0

        session.total_score = total_score
        session.max_score = max_score
        session.status = "graded"
        session.graded_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # Programmatic grading
    # ------------------------------------------------------------------

    def _grade_exact_match(
        self, answer: ExamAnswer, question: PracticeQuestion
    ) -> None:
        """Grade multichoice / numeric via exact match."""
        answer.grading_method = "exact_match"
        answer.graded_at = datetime.now(timezone.utc)

        student = (answer.student_answer or "").strip()
        if not student:
            answer.score = 0.0
            answer.is_correct = False
            answer.ai_feedback = "No answer provided."
            return

        correct = (question.correct_answer or "").strip()
        accepted = question.accepted_answers or []

        if question.question_type == "multichoice":
            normalised_student = student.upper()
            all_accepted = [correct.upper()] + [a.upper() for a in accepted]
            is_correct = normalised_student in all_accepted
        else:
            # numeric
            normalised_student = self._normalize_numeric(student)
            all_accepted = [self._normalize_numeric(correct)] + [
                self._normalize_numeric(a) for a in accepted
            ]
            is_correct = normalised_student in all_accepted

        answer.is_correct = is_correct
        answer.score = answer.max_score if is_correct else 0.0
        answer.ai_feedback = "Correct!" if is_correct else f"Incorrect. Expected: {correct}"

    # ------------------------------------------------------------------
    # AI grading
    # ------------------------------------------------------------------

    async def _grade_ai_batch(
        self, answers_with_questions: list[tuple[ExamAnswer, PracticeQuestion]]
    ) -> None:
        """Grade a batch of explanation questions via Gemini AI."""
        batch_input: list[dict] = []
        answer_map: dict[int, ExamAnswer] = {}

        for answer, question in answers_with_questions:
            batch_input.append(
                {
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "correct_answer": question.correct_answer or "",
                    "answer_explanation": question.answer_explanation,
                    "max_score": answer.max_score,
                    "student_answer": answer.student_answer or "",
                    "subject": question.exam_paper.subject if question.exam_paper else "general",
                }
            )
            answer_map[question.id] = answer

        messages = build_grading_messages(batch_input)
        llm = get_llm(tier="grading", provider="gemini")

        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON array found in AI response")

            results = json.loads(json_match.group())

            for item in results:
                qid = item.get("question_id")
                ans = answer_map.get(qid)
                if not ans:
                    continue

                ans.score = min(float(item.get("score", 0)), ans.max_score)
                ans.is_correct = bool(item.get("is_correct", False))
                ans.ai_feedback = item.get("feedback", "")
                ans.grading_method = "ai_grading"
                ans.graded_at = datetime.now(timezone.utc)

        except Exception:
            logger.exception("AI grading failed for batch, falling back to 0")
            for answer, _question in answers_with_questions:
                answer.score = 0.0
                answer.is_correct = False
                answer.grading_method = "ai_grading"
                answer.ai_feedback = "AI grading failed. Please request manual review."
                answer.graded_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_numeric(value: str) -> str:
        """Strip whitespace and normalize decimal format for comparison."""
        value = value.strip()
        # Remove trailing zeros after decimal point
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        # Remove leading zeros (but keep "0" and "0.x")
        if "." in value:
            int_part, dec_part = value.split(".", 1)
            int_part = int_part.lstrip("0") or "0"
            value = f"{int_part}.{dec_part}"
        else:
            value = value.lstrip("0") or "0"
        return value
