from fastapi import Depends, Request
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.database import get_db
from app.models.user import User
from app.models.subscription_tier import SubscriptionTier

settings = get_settings()

clerk_config = ClerkConfig(jwks_url=settings.clerk_jwks_url) if settings.clerk_jwks_url else None
clerk_auth = ClerkHTTPBearer(config=clerk_config) if clerk_config else None


async def _get_default_tier_id(db: AsyncSession) -> int | None:
    return await db.scalar(
        select(SubscriptionTier.id).where(SubscriptionTier.is_default == True)
    )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify Clerk JWT and return local user. Auto-create on first login."""
    if not clerk_auth:
        raise AuthenticationError(detail="Auth not configured")

    credentials = await clerk_auth(request)
    clerk_id = credentials.decoded.get("sub")
    if not clerk_id:
        raise AuthenticationError(detail="Invalid token: missing sub claim")

    user = await db.scalar(select(User).where(User.clerk_id == clerk_id))

    if not user:
        email = credentials.decoded.get("email", "")
        admin_emails = [e.strip() for e in settings.initial_admin_emails.split(",") if e.strip()]
        role = "admin" if email in admin_emails else "user"

        default_tier_id = await _get_default_tier_id(db)
        user = User(
            clerk_id=clerk_id,
            email=email,
            nickname=credentials.decoded.get("name"),
            role=role,
            tier_id=default_tier_id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise AuthenticationError(detail="Account is deactivated")

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Return authenticated user if Bearer token present, else None."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and len(auth_header) > 10:
        try:
            return await get_current_user(request, db)
        except Exception:
            return None
    return None


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have admin role."""
    if user.role != "admin":
        raise AuthorizationError(detail="Admin access required")
    return user
