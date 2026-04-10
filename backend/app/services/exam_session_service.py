"""Service for managing exam practice sessions."""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.exam_paper import ExamPaper, PracticeQuestion
from app.models.exam_session import ExamAnswer, ExamSession
from app.services.grading_service import GradingService

logger = logging.getLogger(__name__)


class ExamSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Start sessions
    # ------------------------------------------------------------------

    async def start_real_exam(
        self,
        user_id: int,
        exam_paper_id: int,
        mode: str,
        time_limit_minutes: int | None = None,
    ) -> ExamSession:
        """Start a real exam session with all approved questions from an exam paper."""
        # Verify exam paper exists
        result = await self.db.execute(
            select(ExamPaper).where(ExamPaper.id == exam_paper_id)
        )
        paper = result.scalar_one_or_none()
        if not paper:
            raise NotFoundError("Exam paper")

        # Load approved questions
        result = await self.db.execute(
            select(PracticeQuestion)
            .where(
                PracticeQuestion.exam_paper_id == exam_paper_id,
                PracticeQuestion.status == "approved",
            )
            .order_by(PracticeQuestion.order_index)
        )
        questions = result.scalars().all()
        if not questions:
            raise ValidationError("No approved questions found for this exam paper")

        session = ExamSession(
            user_id=user_id,
            exam_paper_id=exam_paper_id,
            session_type="real_exam",
            mode=mode,
            time_limit_minutes=time_limit_minutes,
            status="in_progress",
        )
        self.db.add(session)
        await self.db.flush()

        # Create empty answer records
        for q in questions:
            answer = ExamAnswer(
                session_id=session.id,
                question_id=q.id,
                max_score=float(q.marks) if q.marks and q.marks.isdigit() else 1.0,
            )
            self.db.add(answer)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def start_random_practice(
        self,
        user_id: int,
        subject: str,
        level: int,
        question_types: list[str] | None,
        count: int,
        mode: str,
        time_limit_minutes: int | None = None,
    ) -> ExamSession:
        """Start a random practice session with filtered questions."""
        query = (
            select(PracticeQuestion)
            .join(ExamPaper)
            .where(
                ExamPaper.subject == subject,
                ExamPaper.level == level,
                PracticeQuestion.status == "approved",
            )
        )
        if question_types:
            query = query.where(PracticeQuestion.question_type.in_(question_types))

        query = query.order_by(func.random()).limit(count)
        result = await self.db.execute(query)
        questions = result.scalars().all()

        if not questions:
            raise ValidationError(
                "No approved questions found matching the specified criteria"
            )

        filter_criteria = {
            "subject": subject,
            "level": level,
            "question_types": question_types,
            "count": count,
        }

        session = ExamSession(
            user_id=user_id,
            exam_paper_id=None,
            session_type="random_practice",
            mode=mode,
            time_limit_minutes=time_limit_minutes,
            status="in_progress",
            filter_criteria=filter_criteria,
        )
        self.db.add(session)
        await self.db.flush()

        for q in questions:
            answer = ExamAnswer(
                session_id=session.id,
                question_id=q.id,
                max_score=float(q.marks) if q.marks and q.marks.isdigit() else 1.0,
            )
            self.db.add(answer)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # Answer management
    # ------------------------------------------------------------------

    async def save_answer(
        self, session_id: int, question_id: int, student_answer: str
    ) -> ExamAnswer:
        """Save or update a student's answer for a question in a session."""
        result = await self.db.execute(
            select(ExamAnswer).where(
                ExamAnswer.session_id == session_id,
                ExamAnswer.question_id == question_id,
            )
        )
        answer = result.scalar_one_or_none()
        if not answer:
            raise NotFoundError("Answer record")

        answer.student_answer = student_answer
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    # ------------------------------------------------------------------
    # Submit & grade
    # ------------------------------------------------------------------

    async def submit_session(self, session_id: int) -> ExamSession:
        """Submit a session and trigger grading."""
        result = await self.db.execute(
            select(ExamSession).where(ExamSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Exam session")
        if session.status != "in_progress":
            raise ValidationError(
                f"Session cannot be submitted — current status is '{session.status}'"
            )

        session.status = "submitted"
        session.submitted_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Grade
        grading_service = GradingService(self.db)
        session = await grading_service.grade_session(session_id)
        return session

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_session(self, session_id: int) -> ExamSession:
        """Load a session with its answers."""
        result = await self.db.execute(
            select(ExamSession)
            .options(selectinload(ExamSession.answers))
            .where(ExamSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Exam session")
        return session

    async def get_result(self, session_id: int) -> dict:
        """Return full grading result with per-question scores and explanations."""
        result = await self.db.execute(
            select(ExamSession)
            .options(
                selectinload(ExamSession.answers).selectinload(ExamAnswer.question)
            )
            .where(ExamSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Exam session")
        if session.status != "graded":
            raise ValidationError("Session has not been graded yet")

        # Calculate duration
        duration_minutes = None
        if session.started_at and session.submitted_at:
            delta = session.submitted_at - session.started_at
            duration_minutes = round(delta.total_seconds() / 60, 1)

        # Calculate percentage
        percentage = None
        if session.max_score and session.max_score > 0:
            percentage = round((session.total_score or 0) / session.max_score * 100, 1)

        # Build per-answer results and summary counts
        correct = 0
        partial = 0
        incorrect = 0
        answers_out = []

        for answer in session.answers:
            q = answer.question
            if answer.is_correct:
                correct += 1
            elif (answer.score or 0) > 0:
                partial += 1
            else:
                incorrect += 1

            image_url = f"/api/v1/exams/questions/{q.id}/image" if q.has_image else None

            answers_out.append(
                {
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "student_answer": answer.student_answer,
                    "correct_answer": q.correct_answer,
                    "is_correct": answer.is_correct,
                    "score": answer.score,
                    "max_score": answer.max_score,
                    "grading_method": answer.grading_method,
                    "answer_explanation": q.answer_explanation,
                    "ai_feedback": answer.ai_feedback,
                    "has_image": q.has_image,
                    "image_url": image_url,
                }
            )

        return {
            "session_id": session.id,
            "status": session.status,
            "total_score": session.total_score,
            "max_score": session.max_score,
            "percentage": percentage,
            "duration_minutes": duration_minutes,
            "summary": {
                "total": len(session.answers),
                "correct": correct,
                "partial": partial,
                "incorrect": incorrect,
            },
            "answers": answers_out,
        }

    async def list_sessions(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[ExamSession]:
        """Return paginated session history for a user."""
        result = await self.db.execute(
            select(ExamSession)
            .where(ExamSession.user_id == user_id)
            .order_by(ExamSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
