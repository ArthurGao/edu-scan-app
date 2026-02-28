from typing import AsyncGenerator

from fastapi import Depends
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
