"""Practice question generation and answering endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_or_guest_user, get_db
from app.models.exam_paper import PracticeQuestion
from app.models.practice_answer import PracticeAnswer
from app.models.user import User
from app.schemas.practice import (
    GeneratePracticeResponse,
    PracticeQuestionItem,
    PublicQuestionItem,
    PublicQuestionListResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.practice_generation_service import PracticeGenerationService
from app.services.practice_grading_service import PracticeGradingService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/scan/{scan_id}/generate", response_model=GeneratePracticeResponse)
async def generate_practice(
    scan_id: int,
    refresh: bool = Query(False, description="Force generate new questions"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_or_guest_user),
):
    """Generate or retrieve practice questions for a completed scan."""
    service = PracticeGenerationService(db)
    try:
        questions = await service.get_or_generate(
            scan_id=scan_id,
            user_id=user.id,
            force_refresh=refresh,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Practice generation failed for scan %d", scan_id)
        return GeneratePracticeResponse(
            status="error",
            scan_id=str(scan_id),
            message="Failed to generate practice questions. Please try again.",
        )

    answered_map = await _get_answered_map(db, user.id, [q.id for q in questions])

    items = [
        PracticeQuestionItem(
            id=str(q.id),
            question_text=q.question_text,
            question_type=q.question_type,
            difficulty=q.difficulty,
            difficulty_offset=q.difficulty_offset or 0,
            knowledge_points=q.knowledge_points,
            marks=q.marks,
            answered=q.id in answered_map,
            is_correct=answered_map.get(q.id),
        )
        for q in questions
    ]

    return GeneratePracticeResponse(
        status="ready",
        scan_id=str(scan_id),
        questions=sorted(items, key=lambda x: x.difficulty_offset),
    )


@router.get("/scan/{scan_id}/questions", response_model=GeneratePracticeResponse)
async def get_practice_questions(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_or_guest_user),
):
    """Get existing practice questions for a scan (does not generate)."""
    service = PracticeGenerationService(db)
    questions = await service._get_existing(scan_id, user.id)

    answered_map = await _get_answered_map(db, user.id, [q.id for q in questions])

    items = [
        PracticeQuestionItem(
            id=str(q.id),
            question_text=q.question_text,
            question_type=q.question_type,
            difficulty=q.difficulty,
            difficulty_offset=q.difficulty_offset or 0,
            knowledge_points=q.knowledge_points,
            marks=q.marks,
            answered=q.id in answered_map,
            is_correct=answered_map.get(q.id),
        )
        for q in questions
    ]

    return GeneratePracticeResponse(
        status="ready" if items else "empty",
        scan_id=str(scan_id),
        questions=sorted(items, key=lambda x: x.difficulty_offset),
    )


@router.post("/{question_id}/submit", response_model=SubmitAnswerResponse)
async def submit_answer(
    question_id: int,
    body: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_or_guest_user),
):
    """Submit a student answer and get instant grading result."""
    question = await db.get(PracticeQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    existing = await db.execute(
        select(PracticeAnswer).where(
            PracticeAnswer.user_id == user.id,
            PracticeAnswer.question_id == question_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already answered this question")

    grading = PracticeGradingService(db)
    return await grading.grade_and_save(
        question=question,
        user_id=user.id,
        student_answer=body.student_answer,
        time_spent_seconds=body.time_spent_seconds,
    )


@router.get("/public", response_model=PublicQuestionListResponse)
async def list_public_questions(
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    problem_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Browse public question bank with filters."""
    query = select(PracticeQuestion).where(
        PracticeQuestion.visibility == "public",
        PracticeQuestion.source == "ai_generated",
    )

    if subject:
        query = query.where(
            PracticeQuestion.knowledge_points.op("@>")(f'["{subject}"]')
        )
    if difficulty:
        query = query.where(PracticeQuestion.difficulty == difficulty)
    if problem_type:
        query = query.where(PracticeQuestion.problem_type_tag == problem_type)

    count_query = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(PracticeQuestion.usage_count.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    questions = result.scalars().all()

    items = [
        PublicQuestionItem(
            id=str(q.id),
            question_text=q.question_text,
            question_type=q.question_type,
            difficulty=q.difficulty,
            knowledge_points=q.knowledge_points,
            marks=q.marks,
            usage_count=q.usage_count or 0,
            correct_rate=q.correct_rate,
        )
        for q in questions
    ]

    pages = (total + limit - 1) // limit
    return PublicQuestionListResponse(
        items=items, total=total, page=page, pages=pages
    )


async def _get_answered_map(
    db: AsyncSession, user_id: int, question_ids: list[int]
) -> dict[int, bool]:
    """Return {question_id: is_correct} for answered questions."""
    if not question_ids:
        return {}
    result = await db.execute(
        select(PracticeAnswer.question_id, PracticeAnswer.is_correct).where(
            PracticeAnswer.user_id == user_id,
            PracticeAnswer.question_id.in_(question_ids),
        )
    )
    return {row.question_id: row.is_correct for row in result.all()}
