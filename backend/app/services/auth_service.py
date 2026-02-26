from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.models.user import User
from app.core import security
from app.config import get_settings

settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, request: RegisterRequest) -> TokenResponse:
        """Register a new user and return tokens."""
        # 1. Check if email already exists
        result = await self.db.execute(select(User).where(User.email == request.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # 2. Hash password
        hashed_password = security.get_password_hash(request.password)

        # 3. Create user record
        new_user = User(
            email=request.email,
            password_hash=hashed_password,
            nickname=request.nickname,
            grade_level=request.grade_level,
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        # 4. Generate JWT tokens
        return self._create_tokens(new_user.id)

    async def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens."""
        # 1. Find user by email
        result = await self.db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        # 2. Verify password
        if not user or not security.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # 3. Generate JWT tokens
        return self._create_tokens(user.id)

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        payload = security.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        return self._create_tokens(user_id)

    def _create_tokens(self, user_id: int) -> TokenResponse:
        """Helper to create access and refresh tokens."""
        access_token = security.create_access_token(data={"sub": str(user_id)})
        refresh_token = security.create_refresh_token(data={"sub": str(user_id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )
