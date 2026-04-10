"""AI-powered similar question generation endpoints.

All endpoints require admin privileges.

Endpoints:
  POST   /questions/{question_id}/generate    Generate similar questions from a source
  POST   /exams/{exam_id}/generate            Generate for all questions in an exam
  GET    /questions/pending                    List draft questions (paginated)
  PATCH  /questions/{question_id}/review       Approve or reject a generated question
  PUT    /questions/{question_id}              Edit a generated question
  POST   /sync-to-remote                       Sync approved questions to remote Neon
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.database import get_db
from app.models.exam_paper import PracticeQuestion
from app.schemas.question_gen import (
    GenerateExamRequest,
    GenerateRequest,
    GenerateResponse,
    GeneratedQuestionResponse,
    QuestionEditRequest,
    ReviewRequest,
    SyncResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.question_generator_service import QuestionGeneratorService

router = APIRouter()


# ===========================================================================
# Helpers
# ===========================================================================


def _question_response(q: PracticeQuestion) -> GeneratedQuestionResponse:
    return GeneratedQuestionResponse(
        id=str(q.id),
        exam_paper_id=str(q.exam_paper_id),
        question_number=q.question_number,
        sub_question=q.sub_question,
        question_text=q.question_text,
        question_type=q.question_type,
        correct_answer=q.correct_answer,
        accepted_answers=q.accepted_answers,
        answer_explanation=q.answer_explanation,
        marks=q.marks,
        outcome=q.outcome,
        source=q.source,
        status=q.status,
        source_question_id=str(q.source_question_id) if q.source_question_id else None,
        has_image=q.has_image,
        image_url=f"/api/v1/exams/questions/{q.id}/image" if q.has_image else None,
        created_at=q.created_at,
    )


# ===========================================================================
# Generate similar questions from a single source question
# ===========================================================================


@router.post(
    "/questions/{question_id}/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def generate_similar(
    question_id: int,
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-similar questions from a source question."""
    service = QuestionGeneratorService(db)
    try:
        questions = await service.generate_similar(question_id, count=request.count)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return GenerateResponse(
        questions=[_question_response(q) for q in questions],
        total_generated=len(questions),
    )


# ===========================================================================
# Generate similar questions for all questions in an exam
# ===========================================================================


@router.post(
    "/exams/{exam_id}/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def generate_exam(
    exam_id: int,
    request: GenerateExamRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-similar questions for every original question in an exam."""
    service = QuestionGeneratorService(db)
    try:
        questions = await service.generate_exam(
            exam_id, count_per_question=request.count_per_question
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return GenerateResponse(
        questions=[_question_response(q) for q in questions],
        total_generated=len(questions),
    )


# ===========================================================================
# List pending (draft) questions
# ===========================================================================


@router.get(
    "/questions/pending",
    response_model=PaginatedResponse[GeneratedQuestionResponse],
    dependencies=[Depends(require_admin)],
)
async def list_pending_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List AI-generated questions with draft status, paginated."""
    base = select(PracticeQuestion).where(
        PracticeQuestion.source == "ai_generated",
        PracticeQuestion.status == "draft",
    )
    count_query = select(func.count(PracticeQuestion.id)).where(
        PracticeQuestion.source == "ai_generated",
        PracticeQuestion.status == "draft",
    )

    total = (await db.execute(count_query)).scalar() or 0
    page = (skip // limit) + 1 if limit else 1
    pages = max(1, math.ceil(total / limit))

    query = base.order_by(PracticeQuestion.created_at.desc()).offset(skip).limit(limit)
    questions = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[_question_response(q) for q in questions],
        total=total,
        page=page,
        pages=pages,
        limit=limit,
    )


# ===========================================================================
# Review (approve/reject) a generated question
# ===========================================================================


@router.patch(
    "/questions/{question_id}/review",
    response_model=GeneratedQuestionResponse,
    dependencies=[Depends(require_admin)],
)
async def review_question(
    question_id: int,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject an AI-generated question."""
    question = await db.get(PracticeQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.source != "ai_generated":
        raise HTTPException(status_code=400, detail="Only AI-generated questions can be reviewed")

    question.status = request.status
    await db.commit()
    await db.refresh(question)

    return _question_response(question)


# ===========================================================================
# Edit a generated question
# ===========================================================================


@router.put(
    "/questions/{question_id}",
    response_model=GeneratedQuestionResponse,
    dependencies=[Depends(require_admin)],
)
async def edit_question(
    question_id: int,
    request: QuestionEditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Edit an AI-generated question's content."""
    question = await db.get(PracticeQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if request.question_text is not None:
        question.question_text = request.question_text
    if request.correct_answer is not None:
        question.correct_answer = request.correct_answer
    if request.accepted_answers is not None:
        question.accepted_answers = request.accepted_answers
    if request.answer_explanation is not None:
        question.answer_explanation = request.answer_explanation
    if request.question_type is not None:
        question.question_type = request.question_type

    await db.commit()
    await db.refresh(question)

    return _question_response(question)


# ===========================================================================
# Sync approved AI questions to remote Neon
# ===========================================================================


@router.post(
    "/sync-to-remote",
    response_model=SyncResponse,
    dependencies=[Depends(require_admin)],
)
async def sync_to_remote(
    db: AsyncSession = Depends(get_db),
):
    """Sync all approved, unsynced AI-generated questions to the remote Neon database."""
    service = QuestionGeneratorService(db)
    result = await service.sync_to_remote()

    return SyncResponse(
        synced=result["synced"],
        failed=result["failed"],
        errors=result["errors"],
    )
