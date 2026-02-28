from pydantic import BaseModel


class SettingResponse(BaseModel):
    key: str
    value: object
    description: str | None = None

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    settings: dict[str, object]
