"""Exam practice session endpoints.

Endpoints:
  POST   /sessions/start          Start a real exam session
  POST   /sessions/start-random   Start a random practice session
  PUT    /sessions/{id}/answers/{qid}  Save answer for a question
  POST   /sessions/{id}/submit    Submit and grade a session
  GET    /sessions/{id}           Get session status
  GET    /sessions/{id}/result    Get grading result
  GET    /sessions/               List user's sessions (paginated)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_or_guest_user, get_db
from app.models.user import User
from app.schemas.exam_session import (
    ExamAnswerResult,
    ExamResultResponse,
    ExamSessionResponse,
    SaveAnswerRequest,
    StartExamRequest,
    StartRandomRequest,
)
from app.services.exam_session_service import ExamSessionService

router = APIRouter()


def _session_response(session, question_count: int | None = None) -> dict:
    """Build an ExamSessionResponse-compatible dict from an ExamSession model."""
    count = question_count
    if count is None:
        count = len(session.answers) if hasattr(session, "answers") and session.answers else 0
    return {
        "id": session.id,
        "session_type": session.session_type,
        "mode": session.mode,
        "status": session.status,
        "total_score": session.total_score,
        "max_score": session.max_score,
        "started_at": session.started_at,
        "submitted_at": session.submitted_at,
        "graded_at": session.graded_at,
        "question_count": count,
    }


# ---------------------------------------------------------------------------
# Start sessions
# ---------------------------------------------------------------------------


@router.post("/start", response_model=ExamSessionResponse)
async def start_exam(
    body: StartExamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Start a real exam practice session."""
    service = ExamSessionService(db)
    session = await service.start_real_exam(
        user_id=current_user.id,
        exam_paper_id=body.exam_paper_id,
        mode=body.mode,
        time_limit_minutes=body.time_limit_minutes,
    )
    # Reload to get answers count
    session = await service.get_session(session.id)
    return _session_response(session)


@router.post("/start-random", response_model=ExamSessionResponse)
async def start_random_practice(
    body: StartRandomRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Start a random practice session with filtered questions."""
    service = ExamSessionService(db)
    session = await service.start_random_practice(
        user_id=current_user.id,
        subject=body.subject,
        level=body.level,
        question_types=body.question_types,
        count=body.count,
        mode=body.mode,
        time_limit_minutes=body.time_limit_minutes,
    )
    session = await service.get_session(session.id)
    return _session_response(session)


# ---------------------------------------------------------------------------
# Answer management
# ---------------------------------------------------------------------------


@router.put("/{session_id}/answers/{question_id}")
async def save_answer(
    session_id: int,
    question_id: int,
    body: SaveAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Save a student's answer for a specific question."""
    service = ExamSessionService(db)
    answer = await service.save_answer(session_id, question_id, body.student_answer)
    return {"question_id": answer.question_id, "student_answer": answer.student_answer}


# ---------------------------------------------------------------------------
# Submit & grade
# ---------------------------------------------------------------------------


@router.post("/{session_id}/submit", response_model=ExamSessionResponse)
async def submit_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Submit a session for grading."""
    service = ExamSessionService(db)
    session = await service.submit_session(session_id)
    # Reload with answers to get count
    session = await service.get_session(session.id)
    return _session_response(session)


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------


@router.get("/{session_id}", response_model=ExamSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Get session status and basic info."""
    service = ExamSessionService(db)
    session = await service.get_session(session_id)
    return _session_response(session)


@router.get("/{session_id}/result", response_model=ExamResultResponse)
async def get_result(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Get full grading result (only available after grading)."""
    service = ExamSessionService(db)
    return await service.get_result(session_id)


@router.get("/", response_model=list[ExamSessionResponse])
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """List user's exam sessions (paginated)."""
    service = ExamSessionService(db)
    sessions = await service.list_sessions(current_user.id, skip=skip, limit=limit)
    return [_session_response(s, question_count=0) for s in sessions]
