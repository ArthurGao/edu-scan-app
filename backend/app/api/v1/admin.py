from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import require_admin
from app.database import get_db
from app.models.daily_usage import DailyUsage
from app.models.subscription_tier import SubscriptionTier
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.settings import SettingsUpdate
from app.schemas.tier import TierCreate, TierUpdate
from app.schemas.user import AdminUserUpdate

router = APIRouter(dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/stats/overview")
async def get_stats_overview(db: AsyncSession = Depends(get_db)):
    """KPI stats: total users, active today, questions today, tier distribution."""
    today = date.today()

    total_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active == True)
    )

    active_today = await db.scalar(
        select(func.count(func.distinct(DailyUsage.user_id))).where(
            DailyUsage.usage_date == today
        )
    )

    questions_today = await db.scalar(
        select(func.coalesce(func.sum(DailyUsage.question_count), 0)).where(
            DailyUsage.usage_date == today
        )
    )

    tier_rows = (
        await db.execute(
            select(
                SubscriptionTier.name,
                SubscriptionTier.display_name,
                func.count(User.id).label("user_count"),
            )
            .outerjoin(User, User.tier_id == SubscriptionTier.id)
            .where(SubscriptionTier.is_active == True)
            .group_by(SubscriptionTier.id, SubscriptionTier.name, SubscriptionTier.display_name)
            .order_by(SubscriptionTier.sort_order)
        )
    ).all()

    tier_distribution = [
        {"name": row.name, "display_name": row.display_name, "user_count": row.user_count}
        for row in tier_rows
    ]

    return {
        "total_users": total_users or 0,
        "active_today": active_today or 0,
        "questions_today": questions_today or 0,
        "tier_distribution": tier_distribution,
    }


@router.get("/stats/daily")
async def get_stats_daily(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Daily stats for the last N days."""
    start_date = date.today() - timedelta(days=days - 1)

    rows = (
        await db.execute(
            select(
                DailyUsage.usage_date,
                func.count(func.distinct(DailyUsage.user_id)).label("active_users"),
                func.coalesce(func.sum(DailyUsage.question_count), 0).label("total_questions"),
            )
            .where(DailyUsage.usage_date >= start_date)
            .group_by(DailyUsage.usage_date)
            .order_by(DailyUsage.usage_date)
        )
    ).all()

    return [
        {
            "date": row.usage_date.isoformat(),
            "active_users": row.active_users,
            "total_questions": row.total_questions,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    tier_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Paginated user list with search and filters."""
    query = select(User).options(joinedload(User.tier))

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(pattern)) | (User.nickname.ilike(pattern))
        )
    if role:
        query = query.where(User.role == role)
    if tier_id is not None:
        query = query.where(User.tier_id == tier_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.unique().scalars().all()

    return {
        "items": [
            {
                "id": u.id,
                "clerk_id": u.clerk_id,
                "email": u.email,
                "nickname": u.nickname,
                "avatar_url": u.avatar_url,
                "grade_level": u.grade_level,
                "role": u.role,
                "tier_name": u.tier.name if u.tier else None,
                "tier_id": u.tier_id,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user detail."""
    user = await db.scalar(
        select(User).options(joinedload(User.tier)).where(User.id == user_id)
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get today's usage
    usage = await db.scalar(
        select(DailyUsage.question_count).where(
            DailyUsage.user_id == user_id,
            DailyUsage.usage_date == date.today(),
        )
    )

    return {
        "id": user.id,
        "clerk_id": user.clerk_id,
        "email": user.email,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "grade_level": user.grade_level,
        "role": user.role,
        "tier_name": user.tier.name if user.tier else None,
        "tier_id": user.tier_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "usage_today": usage or 0,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    update: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user role, tier, or active status."""
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.role is not None:
        if update.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'user' or 'admin'.")
        user.role = update.role

    if update.tier_id is not None:
        tier = await db.scalar(
            select(SubscriptionTier).where(SubscriptionTier.id == update.tier_id)
        )
        if not tier:
            raise HTTPException(status_code=400, detail="Tier not found")
        user.tier_id = update.tier_id

    if update.is_active is not None:
        user.is_active = update.is_active

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "tier_id": user.tier_id,
        "is_active": user.is_active,
    }


# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------


@router.get("/tiers")
async def list_tiers(db: AsyncSession = Depends(get_db)):
    """List all tiers with user counts."""
    rows = (
        await db.execute(
            select(
                SubscriptionTier,
                func.count(User.id).label("user_count"),
            )
            .outerjoin(User, User.tier_id == SubscriptionTier.id)
            .group_by(SubscriptionTier.id)
            .order_by(SubscriptionTier.sort_order)
        )
    ).all()

    return [
        {
            "id": tier.id,
            "name": tier.name,
            "display_name": tier.display_name,
            "description": tier.description,
            "daily_question_limit": tier.daily_question_limit,
            "allowed_ai_models": tier.allowed_ai_models,
            "features": tier.features,
            "max_image_size_mb": tier.max_image_size_mb,
            "is_default": tier.is_default,
            "is_active": tier.is_active,
            "sort_order": tier.sort_order,
            "user_count": user_count,
        }
        for tier, user_count in rows
    ]


@router.post("/tiers", status_code=201)
async def create_tier(
    data: TierCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new subscription tier."""
    existing = await db.scalar(
        select(SubscriptionTier).where(SubscriptionTier.name == data.name)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Tier '{data.name}' already exists")

    # If this tier is set as default, unset other defaults
    if data.is_default:
        await _unset_default_tiers(db)

    tier = SubscriptionTier(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        daily_question_limit=data.daily_question_limit,
        allowed_ai_models=data.allowed_ai_models,
        features=data.features,
        max_image_size_mb=data.max_image_size_mb,
        is_default=data.is_default,
        sort_order=data.sort_order,
    )
    db.add(tier)
    await db.commit()
    await db.refresh(tier)

    return {
        "id": tier.id,
        "name": tier.name,
        "display_name": tier.display_name,
        "description": tier.description,
        "daily_question_limit": tier.daily_question_limit,
        "allowed_ai_models": tier.allowed_ai_models,
        "features": tier.features,
        "max_image_size_mb": tier.max_image_size_mb,
        "is_default": tier.is_default,
        "is_active": tier.is_active,
        "sort_order": tier.sort_order,
    }


@router.patch("/tiers/{tier_id}")
async def update_tier(
    tier_id: int,
    data: TierUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a subscription tier."""
    tier = await db.scalar(
        select(SubscriptionTier).where(SubscriptionTier.id == tier_id)
    )
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    update_data = data.model_dump(exclude_unset=True)

    # If setting as default, unset other defaults first
    if update_data.get("is_default"):
        await _unset_default_tiers(db)

    for field, value in update_data.items():
        setattr(tier, field, value)

    await db.commit()
    await db.refresh(tier)

    return {
        "id": tier.id,
        "name": tier.name,
        "display_name": tier.display_name,
        "description": tier.description,
        "daily_question_limit": tier.daily_question_limit,
        "allowed_ai_models": tier.allowed_ai_models,
        "features": tier.features,
        "max_image_size_mb": tier.max_image_size_mb,
        "is_default": tier.is_default,
        "is_active": tier.is_active,
        "sort_order": tier.sort_order,
    }


@router.delete("/tiers/{tier_id}")
async def delete_tier(
    tier_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a tier. Returns 409 if tier still has users assigned."""
    tier = await db.scalar(
        select(SubscriptionTier).where(SubscriptionTier.id == tier_id)
    )
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    user_count = await db.scalar(
        select(func.count()).select_from(User).where(User.tier_id == tier_id)
    )
    if user_count and user_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete tier: {user_count} user(s) still assigned. "
            f"Reassign users before deleting.",
        )

    tier.is_active = False
    await db.commit()

    return {"status": "ok", "message": f"Tier '{tier.name}' has been deactivated."}


async def _unset_default_tiers(db: AsyncSession):
    """Unset is_default on all tiers."""
    result = await db.execute(
        select(SubscriptionTier).where(SubscriptionTier.is_default == True)
    )
    for tier in result.scalars().all():
        tier.is_default = False
    await db.flush()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@router.get("/settings")
async def list_settings(db: AsyncSession = Depends(get_db)):
    """List all system settings."""
    result = await db.execute(
        select(SystemSetting).order_by(SystemSetting.key)
    )
    settings = result.scalars().all()

    return [
        {
            "key": s.key,
            "value": s.value,
            "description": s.description,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in settings
    ]


@router.patch("/settings")
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update one or more system settings."""
    updated = []
    for key, value in data.settings.items():
        setting = await db.scalar(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        if setting:
            setting.value = value
            updated.append(key)
        else:
            new_setting = SystemSetting(key=key, value=value)
            db.add(new_setting)
            updated.append(key)

    await db.commit()

    return {"status": "ok", "updated_keys": updated}
