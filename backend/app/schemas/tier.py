from pydantic import BaseModel


class TierBase(BaseModel):
    display_name: str
    description: str | None = None
    daily_question_limit: int = 5
    allowed_ai_models: list[str] = ["claude"]
    features: dict = {}
    max_image_size_mb: int = 5
    is_default: bool = False
    sort_order: int = 0


class TierCreate(TierBase):
    name: str


class TierUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    daily_question_limit: int | None = None
    allowed_ai_models: list[str] | None = None
    features: dict | None = None
    max_image_size_mb: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class TierResponse(TierBase):
    id: int
    name: str
    is_active: bool
    user_count: int = 0

    model_config = {"from_attributes": True}
