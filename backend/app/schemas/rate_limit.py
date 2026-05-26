from pydantic import BaseModel


class RateLimitCreate(BaseModel):
    name: str
    scope: str = "global"  # global/user/datasource/api
    target_id: int | None = None
    max_per_minute: int | None = None
    max_per_hour: int | None = None
    max_per_day: int | None = None
    max_rows_per_query: int | None = None
    is_active: bool = True


class RateLimitUpdate(BaseModel):
    name: str | None = None
    scope: str | None = None
    target_id: int | None = None
    max_per_minute: int | None = None
    max_per_hour: int | None = None
    max_per_day: int | None = None
    max_rows_per_query: int | None = None
    is_active: bool | None = None


class RateLimitResponse(BaseModel):
    id: int
    name: str
    scope: str
    target_id: int | None = None
    max_per_minute: int | None = None
    max_per_hour: int | None = None
    max_per_day: int | None = None
    max_rows_per_query: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}
