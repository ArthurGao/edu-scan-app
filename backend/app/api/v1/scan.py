from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_or_create_guest_user
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.scan import (
    ScanResponse, FollowUpRequest, FollowUpResponse,
    ConversationResponse, ConversationMessageResponse,
)
from app.services.scan_service import ScanService
from app.services.conversation_service import ConversationService
from app.services.ocr_service import OCRService
from app.services.quota_service import check_and_increment_quota

router = APIRouter()


@router.post("/extract-text")
async def extract_text(
    image: UploadFile = File(...),
):
    """Extract text from an uploaded image using OCR (no solving)."""
    image_bytes = await image.read()
    ocr_service = OCRService()
    text = await ocr_service.extract_text(image_bytes)
    return {"ocr_text": text}


@router.post("/solve", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def solve_problem(
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    ai_provider: Optional[str] = Form(None),
    grade_level: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Solve a homework problem from an uploaded image or typed text.
    At least one of `image` or `text` must be provided.
    Requires authentication.
    """
    if not image and not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'image' or 'text' must be provided.",
        )
    quota = await check_and_increment_quota(user=user, ip_address=None, db=db)
    scan_service = ScanService(db)
    return await scan_service.scan_and_solve(
        user_id=user.id,
        image=image,
        text=text,
        subject=subject,
        ai_provider=ai_provider,
        grade_level=grade_level,
    )


@router.post("/solve-guest", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def solve_problem_guest(
    request: Request,
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    ai_provider: Optional[str] = Form(None),
    grade_level: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """
    Solve a homework problem from an uploaded image or typed text (guest mode).
    At least one of `image` or `text` must be provided.
    """
    if not image and not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'image' or 'text' must be provided.",
        )
    ip_address = request.client.host if request.client else "unknown"
    quota = await check_and_increment_quota(user=None, ip_address=ip_address, db=db)
    scan_service = ScanService(db)
    return await scan_service.scan_and_solve(
        user_id=guest_user.id,
        image=image,
        text=text,
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
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Send a follow-up question about a scan."""
    service = ScanService(db)
    result = await service.followup(
        scan_id=scan_id,
        user_id=guest_user.id,
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
    guest_user: User = Depends(get_or_create_guest_user),
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
