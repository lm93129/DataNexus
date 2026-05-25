from datetime import datetime

from pydantic import BaseModel, Field


class CustomApiCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    mode: str = Field(..., pattern=r"^(low_code|custom)$")
    config_json: str
    is_active: bool = True


class CustomApiUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    mode: str | None = Field(None, pattern=r"^(low_code|custom)$")
    config_json: str | None = None
    is_active: bool | None = None


class CustomApiResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    mode: str
    config_json: str
    is_active: bool
    version: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
