from pydantic import BaseModel


class DatasourceCreate(BaseModel):
    name: str
    type: str  # mysql/postgresql/mssql/oracle
    host: str
    port: int
    database: str
    username: str
    password: str
    description: str | None = None


class DatasourceUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    description: str | None = None


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

    model_config = {"from_attributes": True}
