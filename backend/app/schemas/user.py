from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6)
    role: str = Field(default="viewer", pattern=r"^(admin|analyst|viewer)$")


class UserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(admin|analyst|viewer)$")
    is_active: bool | None = None
    reset_password: str | None = Field(default=None, min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    has_api_key: bool = False
    created_at: str | None = None

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)
