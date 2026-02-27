from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_or_create_guest_user
from app.models.mistake_book import MistakeBook
from app.models.scan_record import ScanRecord
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.mistake import CreateMistakeRequest, MistakeResponse, UpdateMistakeRequest
from app.schemas.scan import ScanRecordResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_mistakes(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    mastered: Optional[bool] = Query(None, description="Filter by mastered status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Get user's mistake book with optional filters."""
    query = (
        select(MistakeBook)
        .options(selectinload(MistakeBook.scan_record))
        .where(MistakeBook.user_id == guest_user.id)
    )
    count_query = select(func.count(MistakeBook.id)).where(
        MistakeBook.user_id == guest_user.id
    )

    if mastered is not None:
        query = query.where(MistakeBook.mastered == mastered)
        count_query = count_query.where(MistakeBook.mastered == mastered)

    if subject:
        query = query.where(MistakeBook.subject == subject)
        count_query = count_query.where(MistakeBook.subject == subject)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query.order_by(MistakeBook.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    mistakes = result.scalars().all()

    items = []
    for m in mistakes:
        sr = m.scan_record
        items.append(
            MistakeResponse(
                id=str(m.id),
                scan_record=ScanRecordResponse(
                    id=str(sr.id),
                    image_url=sr.image_url,
                    ocr_text=sr.ocr_text,
                    subject=sr.subject,
                    difficulty=sr.difficulty,
                    created_at=sr.created_at,
                ),
                notes=m.notes,
                mastered=m.mastered,
                review_count=m.review_count,
                next_review_at=m.next_review_at,
                created_at=m.created_at,
            )
        )

    pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=items, total=total, page=page, pages=pages, limit=limit
    )


@router.post("", response_model=MistakeResponse, status_code=201)
async def add_to_mistakes(
    request: CreateMistakeRequest,
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Add a scan record to mistake book."""
    # Check scan exists
    scan_result = await db.execute(
        select(ScanRecord).where(ScanRecord.id == int(request.scan_id))
    )
    scan_record = scan_result.scalar_one_or_none()
    if not scan_record:
        raise HTTPException(status_code=404, detail="Scan record not found")

    # Check not already in mistakes
    existing = await db.execute(
        select(MistakeBook).where(
            MistakeBook.user_id == guest_user.id,
            MistakeBook.scan_id == int(request.scan_id),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already in mistake book")

    mistake = MistakeBook(
        user_id=guest_user.id,
        scan_id=int(request.scan_id),
        subject=scan_record.subject,
        notes=request.notes,
        next_review_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(mistake)
    await db.commit()
    await db.refresh(mistake)

    return MistakeResponse(
        id=str(mistake.id),
        scan_record=ScanRecordResponse(
            id=str(scan_record.id),
            image_url=scan_record.image_url,
            ocr_text=scan_record.ocr_text,
            subject=scan_record.subject,
            difficulty=scan_record.difficulty,
            created_at=scan_record.created_at,
        ),
        notes=mistake.notes,
        mastered=mistake.mastered,
        review_count=mistake.review_count,
        next_review_at=mistake.next_review_at,
        created_at=mistake.created_at,
    )


@router.patch("/{mistake_id}", response_model=MistakeResponse)
async def update_mistake(
    mistake_id: int,
    request: UpdateMistakeRequest,
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Update a mistake book entry (notes, mastered status)."""
    result = await db.execute(
        select(MistakeBook)
        .options(selectinload(MistakeBook.scan_record))
        .where(MistakeBook.id == mistake_id, MistakeBook.user_id == guest_user.id)
    )
    mistake = result.scalar_one_or_none()
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")

    if request.notes is not None:
        mistake.notes = request.notes
    if request.mastered is not None:
        mistake.mastered = request.mastered

    await db.commit()
    await db.refresh(mistake)
    sr = mistake.scan_record

    return MistakeResponse(
        id=str(mistake.id),
        scan_record=ScanRecordResponse(
            id=str(sr.id),
            image_url=sr.image_url,
            ocr_text=sr.ocr_text,
            subject=sr.subject,
            difficulty=sr.difficulty,
            created_at=sr.created_at,
        ),
        notes=mistake.notes,
        mastered=mistake.mastered,
        review_count=mistake.review_count,
        next_review_at=mistake.next_review_at,
        created_at=mistake.created_at,
    )


@router.delete("/{mistake_id}")
async def delete_mistake(
    mistake_id: int,
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Remove an entry from mistake book."""
    result = await db.execute(
        select(MistakeBook).where(
            MistakeBook.id == mistake_id, MistakeBook.user_id == guest_user.id
        )
    )
    mistake = result.scalar_one_or_none()
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    await db.delete(mistake)
    await db.commit()
    return {"message": "Deleted successfully"}
