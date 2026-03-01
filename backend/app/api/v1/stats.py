from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_or_guest_user
from app.models.user import User
from app.models.learning_stats import LearningStats
from app.models.scan_record import ScanRecord
from app.models.mistake_book import MistakeBook
from app.schemas.stats import StatsSummaryResponse, DailyStatResponse

router = APIRouter()


@router.get("/summary", response_model=StatsSummaryResponse)
async def get_stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Get learning stats summary for current user."""
    scan_result = await db.execute(
        select(func.count(ScanRecord.id))
        .where(ScanRecord.user_id == current_user.id)
    )
    total_scans = scan_result.scalar() or 0

    mastered_result = await db.execute(
        select(func.count(MistakeBook.id))
        .where(MistakeBook.user_id == current_user.id, MistakeBook.mastered == True)
    )
    total_mastered = mastered_result.scalar() or 0

    avg_result = await db.execute(
        select(func.avg(LearningStats.avg_quality_score))
        .where(LearningStats.user_id == current_user.id)
    )
    avg_quality = avg_result.scalar() or 0.0

    subject_result = await db.execute(
        select(ScanRecord.subject, func.count(ScanRecord.id))
        .where(ScanRecord.user_id == current_user.id, ScanRecord.subject.isnot(None))
        .group_by(ScanRecord.subject)
    )
    subjects = {row[0]: row[1] for row in subject_result.all()}

    return StatsSummaryResponse(
        total_scans=total_scans,
        total_mastered=total_mastered,
        avg_quality=round(float(avg_quality), 2),
        subjects=subjects,
    )


@router.get("/daily", response_model=list[DailyStatResponse])
async def get_daily_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Get daily learning stats."""
    cutoff = datetime.utcnow().date() - timedelta(days=days)

    result = await db.execute(
        select(LearningStats)
        .where(
            LearningStats.user_id == current_user.id,
            LearningStats.stat_date >= cutoff,
        )
        .order_by(LearningStats.stat_date.desc())
    )
    stats = result.scalars().all()
    return [DailyStatResponse.model_validate(s) for s in stats]
