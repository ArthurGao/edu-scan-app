from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_or_create_guest_user
from app.models.scan_record import ScanRecord
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.scan import ScanRecordResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_history(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Get user's scan history with optional filters."""
    query = select(ScanRecord).where(ScanRecord.user_id == guest_user.id)
    count_query = select(func.count(ScanRecord.id)).where(
        ScanRecord.user_id == guest_user.id
    )

    if subject:
        query = query.where(ScanRecord.subject == subject)
        count_query = count_query.where(ScanRecord.subject == subject)
    if start_date:
        query = query.where(ScanRecord.created_at >= start_date)
        count_query = count_query.where(ScanRecord.created_at >= start_date)
    if end_date:
        query = query.where(ScanRecord.created_at <= end_date)
        count_query = count_query.where(ScanRecord.created_at <= end_date)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ScanRecord.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    items = [
        ScanRecordResponse(
            id=str(r.id),
            image_url=r.image_url,
            ocr_text=r.ocr_text,
            subject=r.subject,
            difficulty=r.difficulty,
            created_at=r.created_at,
        )
        for r in records
    ]

    pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=items, total=total, page=page, pages=pages, limit=limit
    )


@router.delete("/{scan_id}")
async def delete_history_item(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    guest_user: User = Depends(get_or_create_guest_user),
):
    """Delete a scan record from history."""
    result = await db.execute(
        select(ScanRecord).where(
            ScanRecord.id == scan_id, ScanRecord.user_id == guest_user.id
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.delete(record)
    await db.commit()
    return {"message": "Deleted successfully"}
