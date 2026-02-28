from datetime import datetime
from pydantic import BaseModel


class TierInfo(BaseModel):
    name: str
    display_name: str
    daily_question_limit: int
    allowed_ai_models: list[str]
    features: dict


class UsageInfo(BaseModel):
    limit: int
    used: int
    remaining: int


class UserResponse(BaseModel):
    id: int
    clerk_id: str | None = None
    email: str
    nickname: str | None = None
    avatar_url: str | None = None
    grade_level: str | None = None
    role: str
    tier_name: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    tier: TierInfo | None = None
    usage_today: UsageInfo | None = None


class AdminUserUpdate(BaseModel):
    role: str | None = None
    tier_id: int | None = None
    is_active: bool | None = None
