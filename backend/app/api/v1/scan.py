from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db, get_or_create_guest_user
from app.models.user import User
from app.schemas.scan import (
    ScanResponse, FollowUpRequest, FollowUpResponse,
    ConversationResponse, ConversationMessageResponse,
)
from app.services.scan_service import ScanService
from app.services.conversation_service import ConversationService

router = APIRouter()


@router.post("/solve", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def solve_problem(
    image: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    ai_provider: Optional[str] = Form(None),
    grade_level: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a homework problem image, perform OCR, and get a solution from AI.
    """
    scan_service = ScanService(db)
    return await scan_service.scan_and_solve(
        user_id=current_user.id,
        image=image,
        subject=subject,
        ai_provider=ai_provider,
        grade_level=grade_level
    )


@router.post("/solve-guest", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def solve_problem_guest(
    image: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    ai_provider: Optional[str] = Form(None),
    grade_level: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """
    Upload a homework problem image without authentication (guest mode).
    Uses a shared guest user account.
    """
    scan_service = ScanService(db)
    return await scan_service.scan_and_solve(
        user_id=guest_user.id,
        image=image,
        subject=subject,
        ai_provider=ai_provider,
        grade_level=grade_level,
    )


@router.get("/stream/{scan_id}")
async def stream_solution(scan_id: str, db: AsyncSession = Depends(get_db)):
    """
    Stream solution response using Server-Sent Events.

    Events:
    - ocr_complete: OCR text extracted
    - solution_chunk: Partial solution content
    - complete: Solution finished
    """
    # TODO: Implement SSE streaming
    pass


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan_result(scan_id: int, db: AsyncSession = Depends(get_db)):
    """Get a previously scanned problem and its solution."""
    scan_service = ScanService(db)
    result = await scan_service.get_scan_result(scan_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result


@router.post("/{scan_id}/followup", response_model=FollowUpResponse)
async def followup(
    scan_id: int,
    request: FollowUpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a follow-up question about a scan."""
    service = ScanService(db)
    result = await service.followup(
        scan_id=scan_id,
        user_id=current_user.id,
        message=request.message,
    )
    return FollowUpResponse(
        reply=result["reply"],
        tokens_used=result.get("tokens_used", 0),
    )


@router.get("/{scan_id}/conversation", response_model=ConversationResponse)
async def get_conversation(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation history for a scan."""
    service = ConversationService(db)
    history = await service.get_history(scan_id)
    return ConversationResponse(
        messages=[
            ConversationMessageResponse(
                id=str(i),
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"],
            )
            for i, msg in enumerate(history)
        ],
        total_messages=len(history),
    )
