from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.subscription_tier import SubscriptionTier
from app.models.user import User

router = APIRouter()
settings = get_settings()


async def _verify_webhook(request: Request) -> dict:
    """Verify Clerk webhook signature using svix."""
    from svix.webhooks import Webhook, WebhookVerificationError

    body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    if not settings.clerk_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        wh = Webhook(settings.clerk_webhook_secret)
        payload = wh.verify(body, headers)
        return payload
    except WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")


@router.post("/clerk")
async def handle_clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await _verify_webhook(request)
    event_type = payload.get("type")
    data = payload.get("data", {})

    if event_type == "user.created":
        await _handle_user_created(data, db)
    elif event_type == "user.updated":
        await _handle_user_updated(data, db)
    elif event_type == "user.deleted":
        await _handle_user_deleted(data, db)

    return {"status": "ok"}


async def _handle_user_created(data: dict, db: AsyncSession):
    clerk_id = data.get("id")
    email = _extract_email(data)

    existing = await db.scalar(select(User).where(User.clerk_id == clerk_id))
    if existing:
        return

    default_tier = await db.scalar(
        select(SubscriptionTier.id).where(SubscriptionTier.is_default == True)
    )

    admin_emails = [e.strip() for e in settings.initial_admin_emails.split(",") if e.strip()]
    role = "admin" if email in admin_emails else "user"

    user = User(
        clerk_id=clerk_id,
        email=email,
        nickname=_extract_name(data),
        avatar_url=data.get("image_url"),
        role=role,
        tier_id=default_tier,
    )
    db.add(user)
    await db.commit()


async def _handle_user_updated(data: dict, db: AsyncSession):
    clerk_id = data.get("id")
    user = await db.scalar(select(User).where(User.clerk_id == clerk_id))
    if not user:
        return

    user.email = _extract_email(data) or user.email
    user.nickname = _extract_name(data) or user.nickname
    user.avatar_url = data.get("image_url") or user.avatar_url
    await db.commit()


async def _handle_user_deleted(data: dict, db: AsyncSession):
    clerk_id = data.get("id")
    user = await db.scalar(select(User).where(User.clerk_id == clerk_id))
    if user:
        user.is_active = False
        await db.commit()


def _extract_email(data: dict) -> str:
    addresses = data.get("email_addresses", [])
    primary_id = data.get("primary_email_address_id")
    for addr in addresses:
        if addr.get("id") == primary_id:
            return addr.get("email_address", "")
    return addresses[0].get("email_address", "") if addresses else ""


def _extract_name(data: dict) -> str | None:
    first = data.get("first_name") or ""
    last = data.get("last_name") or ""
    name = f"{first} {last}".strip()
    return name or None
