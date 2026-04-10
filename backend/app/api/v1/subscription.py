"""Subscription tier and usage endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_or_guest_user
from app.core.security import require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.subscription import (
    AdminSetTierRequest,
    SubscriptionInfoResponse,
    UsageHistoryResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/me", response_model=SubscriptionInfoResponse)
async def get_subscription_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Return current user's subscription tier and today's usage."""
    service = SubscriptionService(db)
    info = await service.get_subscription_info(current_user.id)
    return info


@router.get("/usage", response_model=list[UsageHistoryResponse])
async def get_usage_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Return usage history (last 30 days) for the current user."""
    service = SubscriptionService(db)
    history = await service.get_usage_history(current_user.id)
    return history


@router.post("/admin/{user_id}", status_code=status.HTTP_200_OK)
async def admin_set_user_tier(
    user_id: int,
    body: AdminSetTierRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: set a user's subscription tier."""
    service = SubscriptionService(db)
    try:
        await service.set_user_tier(user_id, body.tier_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"detail": f"User {user_id} tier set to '{body.tier_name}'"}
