from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core import security
from app.core.security import get_password_hash

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.app_env}/v1/auth/login")

GUEST_EMAIL = "guest@eduscan.local"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Dependency for getting the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = security.decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_or_create_guest_user(db: AsyncSession = Depends(get_db)) -> User:
    """Dependency for getting or creating a guest user for unauthenticated access."""
    result = await db.execute(select(User).where(User.email == GUEST_EMAIL))
    guest = result.scalar_one_or_none()
    if not guest:
        guest = User(
            email=GUEST_EMAIL,
            password_hash=get_password_hash("guest-no-login"),
            nickname="Guest",
            is_active=True,
        )
        db.add(guest)
        await db.commit()
        await db.refresh(guest)
    return guest
