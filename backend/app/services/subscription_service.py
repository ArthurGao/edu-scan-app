import logging
from datetime import date, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_usage import DailyUsage
from app.models.guest_usage import GuestUsage
from app.models.subscription_tier import SubscriptionTier
from app.models.user import User

logger = logging.getLogger(__name__)

GUEST_DAILY_LIMIT = 10


class SubscriptionService:
    """Service for subscription tier management and usage tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_tier(self, user_id: int) -> str:
        """Return the tier name for a user ('free' if no tier or tier inactive)."""
        result = await self.db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.tier))
        )
        user = result.scalar_one_or_none()
        if not user or not user.tier or not user.tier.is_active:
            return "free"
        return user.tier.name

    async def _get_tier_for_user(self, user_id: int) -> SubscriptionTier | None:
        """Internal: fetch the user's active tier object."""
        result = await self.db.execute(
            select(SubscriptionTier)
            .join(User, User.tier_id == SubscriptionTier.id)
            .where(User.id == user_id, SubscriptionTier.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _get_today_usage(self, user_id: int) -> int:
        """Get question count for today."""
        result = await self.db.scalar(
            select(DailyUsage.question_count).where(
                DailyUsage.user_id == user_id,
                DailyUsage.usage_date == date.today(),
            )
        )
        return result or 0

    async def check_usage_limit(self, user_id: int) -> tuple[bool, int]:
        """Check if user is within daily limit. Returns (allowed, remaining)."""
        tier = await self._get_tier_for_user(user_id)
        if not tier:
            # No tier — use default free limit of 5
            daily_limit = 5
        else:
            daily_limit = tier.daily_question_limit

        used = await self._get_today_usage(user_id)
        remaining = max(0, daily_limit - used)
        return remaining > 0, remaining

    async def increment_usage(self, user_id: int) -> None:
        """UPSERT today's usage, incrementing question_count by 1."""
        stmt = pg_insert(DailyUsage).values(
            user_id=user_id,
            usage_date=date.today(),
            question_count=1,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_daily_usage_user_date",
            set_={"question_count": DailyUsage.question_count + 1},
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def check_guest_usage(self, ip_hash: str) -> tuple[bool, int]:
        """Check guest usage limit (10/day). Returns (allowed, remaining)."""
        result = await self.db.scalar(
            select(GuestUsage.question_count).where(
                GuestUsage.ip_hash == ip_hash,
                GuestUsage.usage_date == date.today(),
            )
        )
        used = result or 0
        remaining = max(0, GUEST_DAILY_LIMIT - used)
        return remaining > 0, remaining

    async def increment_guest_usage(self, ip_hash: str) -> None:
        """UPSERT today's guest usage, incrementing question_count by 1."""
        stmt = pg_insert(GuestUsage).values(
            ip_hash=ip_hash,
            usage_date=date.today(),
            question_count=1,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_guest_usage_ip_date",
            set_={"question_count": GuestUsage.question_count + 1},
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_subscription_info(self, user_id: int) -> dict:
        """Return tier info + today's usage for the /me endpoint."""
        tier = await self._get_tier_for_user(user_id)
        used = await self._get_today_usage(user_id)

        if not tier:
            return {
                "tier_name": "free",
                "display_name": "Free",
                "daily_limit": 5,
                "used_today": used,
                "remaining_today": max(0, 5 - used),
                "features": {},
            }

        return {
            "tier_name": tier.name,
            "display_name": tier.display_name,
            "daily_limit": tier.daily_question_limit,
            "used_today": used,
            "remaining_today": max(0, tier.daily_question_limit - used),
            "features": tier.features or {},
        }

    async def get_usage_history(self, user_id: int, days: int = 30) -> list[dict]:
        """Return usage history for the last N days."""
        since = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(DailyUsage)
            .where(
                DailyUsage.user_id == user_id,
                DailyUsage.usage_date >= since,
            )
            .order_by(DailyUsage.usage_date.desc())
        )
        rows = result.scalars().all()
        return [
            {"date": row.usage_date, "question_count": row.question_count}
            for row in rows
        ]

    async def set_user_tier(self, user_id: int, tier_name: str) -> None:
        """Admin: set a user's subscription tier by name."""
        tier = await self.db.scalar(
            select(SubscriptionTier).where(SubscriptionTier.name == tier_name)
        )
        if not tier:
            raise ValueError(f"Tier '{tier_name}' not found")

        await self.db.execute(
            update(User).where(User.id == user_id).values(tier_id=tier.id)
        )
        await self.db.commit()
