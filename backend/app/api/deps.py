from typing import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User

GUEST_EMAIL = "guest@eduscan.local"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_or_create_guest_user(db: AsyncSession = Depends(get_db)) -> User:
    """Dependency for getting or creating a guest user for unauthenticated access."""
    result = await db.execute(select(User).where(User.email == GUEST_EMAIL))
    guest = result.scalar_one_or_none()
    if not guest:
        guest = User(
            email=GUEST_EMAIL,
            nickname="Guest",
            is_active=True,
        )
        db.add(guest)
        await db.commit()
        await db.refresh(guest)
    return guest


async def get_current_or_guest_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Use Clerk-authenticated user if Bearer token present, else fall back to guest."""
    from app.core.security import get_optional_user

    user = await get_optional_user(request, db)
    if user:
        return user
    return await get_or_create_guest_user(db)
