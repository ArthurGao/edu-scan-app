import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_usage import DailyUsage
from app.models.guest_usage import GuestUsage
from app.models.system_setting import SystemSetting
from app.models.user import User


@dataclass
class QuotaInfo:
    limit: int
    used: int
    remaining: int


async def get_setting_value(key: str, db: AsyncSession, default=None):
    result = await db.scalar(
        select(SystemSetting.value).where(SystemSetting.key == key)
    )
    return result if result is not None else default


async def check_and_increment_quota(
    user: User | None,
    ip_address: str | None,
    db: AsyncSession,
) -> QuotaInfo:
    """Check quota and increment usage. Raises 429 if exceeded."""
    if user:
        return await _check_user_quota(user, db)
    elif ip_address:
        return await _check_guest_quota(ip_address, db)
    else:
        raise HTTPException(status_code=401, detail="Authentication required")


async def get_quota_status(
    user: User | None,
    ip_address: str | None,
    db: AsyncSession,
) -> QuotaInfo:
    """Get current quota without incrementing."""
    if user:
        limit = user.tier.daily_question_limit if user.tier else 5
        usage = await _get_user_usage(user.id, db)
        used = usage.question_count if usage else 0
    elif ip_address:
        limit = await get_setting_value("guest_daily_limit", db, default=3)
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
        usage = await _get_guest_usage_by_hash(ip_hash, db)
        used = usage.question_count if usage else 0
    else:
        return QuotaInfo(limit=0, used=0, remaining=0)

    remaining = -1 if limit == 0 else max(0, limit - used)
    return QuotaInfo(limit=limit, used=used, remaining=remaining)


async def _check_user_quota(user: User, db: AsyncSession) -> QuotaInfo:
    limit = user.tier.daily_question_limit if user.tier else 5
    if limit == 0:
        usage = await _get_or_create_user_usage(user.id, db)
        usage.question_count += 1
        await db.flush()
        return QuotaInfo(limit=0, used=usage.question_count, remaining=-1)

    usage = await _get_or_create_user_usage(user.id, db)

    if usage.question_count >= limit:
        today = date.today()
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_quota_exceeded",
                "message": f"You've reached your daily limit of {limit} questions.",
                "limit": limit,
                "used": usage.question_count,
                "reset_at": (today + timedelta(days=1)).isoformat(),
            },
        )

    usage.question_count += 1
    await db.flush()
    return QuotaInfo(
        limit=limit,
        used=usage.question_count,
        remaining=limit - usage.question_count,
    )


async def _check_guest_quota(ip_address: str, db: AsyncSession) -> QuotaInfo:
    limit = await get_setting_value("guest_daily_limit", db, default=3)
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
    usage = await _get_or_create_guest_usage(ip_hash, db)

    if usage.question_count >= limit:
        today = date.today()
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_quota_exceeded",
                "message": f"Guest limit of {limit} questions reached. Sign up for more!",
                "limit": limit,
                "used": usage.question_count,
                "reset_at": (today + timedelta(days=1)).isoformat(),
            },
        )

    usage.question_count += 1
    await db.flush()
    return QuotaInfo(
        limit=limit,
        used=usage.question_count,
        remaining=limit - usage.question_count,
    )


async def _get_user_usage(user_id: int, db: AsyncSession) -> DailyUsage | None:
    return await db.scalar(
        select(DailyUsage).where(
            DailyUsage.user_id == user_id,
            DailyUsage.usage_date == date.today(),
        )
    )


async def _get_or_create_user_usage(user_id: int, db: AsyncSession) -> DailyUsage:
    usage = await _get_user_usage(user_id, db)
    if not usage:
        usage = DailyUsage(user_id=user_id, usage_date=date.today(), question_count=0)
        db.add(usage)
        await db.flush()
    return usage


async def _get_guest_usage_by_hash(ip_hash: str, db: AsyncSession) -> GuestUsage | None:
    return await db.scalar(
        select(GuestUsage).where(
            GuestUsage.ip_hash == ip_hash,
            GuestUsage.usage_date == date.today(),
        )
    )


async def _get_or_create_guest_usage(ip_hash: str, db: AsyncSession) -> GuestUsage:
    usage = await _get_guest_usage_by_hash(ip_hash, db)
    if not usage:
        usage = GuestUsage(ip_hash=ip_hash, usage_date=date.today(), question_count=0)
        db.add(usage)
        await db.flush()
    return usage
