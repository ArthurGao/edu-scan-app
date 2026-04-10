"""Service for generating similar practice questions using AI."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.database import _fix_db_url
from app.llm.prompts.generate_similar import build_generate_similar_messages
from app.llm.registry import select_llm
from app.models.exam_paper import ExamPaper, PracticeQuestion
from app.utils.tikz_renderer import render_tikz_to_png

logger = logging.getLogger(__name__)


def _extract_json_array(content: str) -> list[dict[str, Any]]:
    """Extract a JSON array from LLM response content.

    Handles cases where the LLM wraps JSON in markdown code fences.
    """
    # Try direct parse first
    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the content
    start = content.find("[")
    end = content.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            result = json.loads(content[start:end])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning("Could not extract JSON array from LLM response")
    return []


class QuestionGeneratorService:
    """Generate similar practice questions using AI."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_similar(
        self, question_id: int, count: int = 3
    ) -> list[PracticeQuestion]:
        """Generate similar questions from a source question.

        Loads the source question and its exam paper, calls the LLM,
        parses the response, optionally renders TikZ diagrams, and
        creates new PracticeQuestion records with source='ai_generated'
        and status='draft'.
        """
        # Load source question with exam paper
        query = (
            select(PracticeQuestion)
            .where(PracticeQuestion.id == question_id)
        )
        source = (await self.db.execute(query)).scalar_one_or_none()
        if not source:
            raise ValueError(f"Question {question_id} not found")

        exam = await self.db.get(ExamPaper, source.exam_paper_id)
        if not exam:
            raise ValueError(f"Exam paper {source.exam_paper_id} not found")

        # Build prompt and call LLM
        messages = build_generate_similar_messages(
            question_text=source.question_text,
            correct_answer=source.correct_answer,
            answer_explanation=source.answer_explanation,
            question_type=source.question_type,
            marks=source.marks,
            outcome=source.outcome,
            count=count,
        )

        llm = select_llm(preferred=None, subject=exam.subject)
        # Override temperature for generation diversity
        llm.temperature = 0.7

        result = await llm.ainvoke(messages)
        generated = _extract_json_array(result.content)

        if not generated:
            logger.warning("LLM returned no valid questions for source %d", question_id)
            return []

        # Create PracticeQuestion records
        new_questions: list[PracticeQuestion] = []
        for i, item in enumerate(generated[:count]):
            # Render TikZ if present
            image_data = None
            has_image = False
            tikz_code = item.get("tikz_code")
            if tikz_code:
                png_bytes = await render_tikz_to_png(tikz_code)
                if png_bytes:
                    image_data = png_bytes
                    has_image = True

            question = PracticeQuestion(
                exam_paper_id=source.exam_paper_id,
                question_number=source.question_number,
                sub_question=f"{source.sub_question}_gen{i + 1}",
                question_text=item.get("question_text", ""),
                question_type=item.get("question_type", source.question_type),
                correct_answer=item.get("correct_answer"),
                accepted_answers=item.get("accepted_answers"),
                answer_explanation=item.get("answer_explanation"),
                marks=source.marks,
                outcome=source.outcome,
                has_image=has_image,
                image_data=image_data,
                order_index=source.order_index + i + 1,
                source="ai_generated",
                status="draft",
                source_question_id=source.id,
            )
            self.db.add(question)
            new_questions.append(question)

        await self.db.flush()
        for q in new_questions:
            await self.db.refresh(q)
        await self.db.commit()

        return new_questions

    async def generate_exam(
        self, exam_id: int, count_per_question: int = 3
    ) -> list[PracticeQuestion]:
        """Generate similar questions for all original approved questions in an exam."""
        exam = await self.db.get(ExamPaper, exam_id)
        if not exam:
            raise ValueError(f"Exam paper {exam_id} not found")

        # Load all original approved questions for this exam
        query = (
            select(PracticeQuestion)
            .where(
                PracticeQuestion.exam_paper_id == exam_id,
                PracticeQuestion.source == "original",
                PracticeQuestion.status == "approved",
            )
            .order_by(PracticeQuestion.order_index)
        )
        originals = (await self.db.execute(query)).scalars().all()

        all_generated: list[PracticeQuestion] = []
        for original in originals:
            try:
                generated = await self.generate_similar(
                    original.id, count=count_per_question
                )
                all_generated.extend(generated)
            except Exception as e:
                logger.warning(
                    "Failed to generate for question %d: %s", original.id, e
                )
                continue

        return all_generated

    async def sync_to_remote(self) -> dict[str, Any]:
        """Sync approved, unsynced AI-generated questions to the remote Neon database.

        Returns a summary dict with synced count, failed count, and error messages.
        """
        settings = get_settings()
        if not settings.remote_database_url:
            return {"synced": 0, "failed": 0, "errors": ["remote_database_url not configured"]}

        # Query local approved + unsynced AI questions
        query = (
            select(PracticeQuestion)
            .where(
                PracticeQuestion.source == "ai_generated",
                PracticeQuestion.status == "approved",
                PracticeQuestion.synced_at.is_(None),
            )
        )
        questions = (await self.db.execute(query)).scalars().all()

        if not questions:
            return {"synced": 0, "failed": 0, "errors": []}

        # Connect to remote Neon
        remote_url = _fix_db_url(settings.remote_database_url)
        remote_engine = create_async_engine(remote_url, echo=False)

        synced = 0
        failed = 0
        errors: list[str] = []

        try:
            async with remote_engine.begin() as conn:
                for q in questions:
                    try:
                        await conn.execute(
                            text("""
                                INSERT INTO practice_questions (
                                    exam_paper_id, question_number, sub_question,
                                    question_text, question_type, correct_answer,
                                    accepted_answers, answer_explanation, marks,
                                    outcome, has_image, image_data, order_index,
                                    source, status, source_question_id, created_at
                                ) VALUES (
                                    :exam_paper_id, :question_number, :sub_question,
                                    :question_text, :question_type, :correct_answer,
                                    :accepted_answers, :answer_explanation, :marks,
                                    :outcome, :has_image, :image_data, :order_index,
                                    :source, :status, :source_question_id, :created_at
                                )
                            """),
                            {
                                "exam_paper_id": q.exam_paper_id,
                                "question_number": q.question_number,
                                "sub_question": q.sub_question,
                                "question_text": q.question_text,
                                "question_type": q.question_type,
                                "correct_answer": q.correct_answer,
                                "accepted_answers": json.dumps(q.accepted_answers)
                                if q.accepted_answers
                                else None,
                                "answer_explanation": q.answer_explanation,
                                "marks": q.marks,
                                "outcome": q.outcome,
                                "has_image": q.has_image,
                                "image_data": q.image_data,
                                "order_index": q.order_index,
                                "source": q.source,
                                "status": q.status,
                                "source_question_id": q.source_question_id,
                                "created_at": q.created_at,
                            },
                        )

                        # Mark as synced locally
                        q.synced_at = datetime.now(timezone.utc)
                        synced += 1

                    except Exception as e:
                        failed += 1
                        errors.append(f"Question {q.id}: {str(e)}")
                        logger.warning("Failed to sync question %d: %s", q.id, e)

            # Commit local synced_at updates
            await self.db.commit()

        except Exception as e:
            errors.append(f"Remote connection error: {str(e)}")
            logger.exception("Failed to connect to remote database")
        finally:
            await remote_engine.dispose()

        return {"synced": synced, "failed": failed, "errors": errors}
