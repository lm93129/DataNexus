from pydantic import BaseModel, Field


class DatasourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern=r"^(mysql|postgresql|mssql|oracle)$")
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    table_blacklist: str | None = "[]"
    column_blacklist: str | None = "[]"


class DatasourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=500)
    table_blacklist: str | None = None
    column_blacklist: str | None = None


class DatasourceResponse(BaseModel):
    id: int
    name: str
    type: str
    host: str
    port: int
    database: str
    username: str
    is_active: bool
    description: str | None = None
    table_blacklist: str | None = "[]"
    column_blacklist: str | None = "[]"

    model_config = {"from_attributes": True}
