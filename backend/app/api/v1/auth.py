from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import get_current_user
from app.database import get_db
from app.models.daily_usage import DailyUsage
from app.models.user import User
from app.schemas.user import TierInfo, UsageInfo, UserProfileResponse

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile with tier and usage info."""
    # Eagerly load tier if not already loaded
    if user.tier_id and not user.tier:
        from app.models.subscription_tier import SubscriptionTier
        await db.refresh(user, ["tier"])

    tier_info = None
    if user.tier:
        tier_info = TierInfo(
            name=user.tier.name,
            display_name=user.tier.display_name,
            daily_question_limit=user.tier.daily_question_limit,
            allowed_ai_models=user.tier.allowed_ai_models,
            features=user.tier.features,
        )

    usage = await db.scalar(
        select(DailyUsage.question_count).where(
            DailyUsage.user_id == user.id,
            DailyUsage.usage_date == date.today(),
        )
    )
    used = usage or 0
    limit = user.tier.daily_question_limit if user.tier else 5
    remaining = -1 if limit == 0 else max(0, limit - used)

    return UserProfileResponse(
        id=user.id,
        clerk_id=user.clerk_id,
        email=user.email,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        grade_level=user.grade_level,
        role=user.role,
        tier_name=user.tier.name if user.tier else None,
        is_active=user.is_active,
        created_at=user.created_at,
        tier=tier_info,
        usage_today=UsageInfo(limit=limit, used=used, remaining=remaining),
    )
