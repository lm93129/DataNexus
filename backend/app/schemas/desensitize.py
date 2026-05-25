from datetime import datetime

from pydantic import BaseModel, Field


class DesensitizeRuleCreate(BaseModel):
    name: str = Field(..., max_length=100)
    pattern: str
    mask_strategy: str = Field(..., max_length=50)
    replacement: str | None = None


class DesensitizeRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    pattern: str | None = None
    mask_strategy: str | None = Field(None, max_length=50)
    replacement: str | None = None


class DesensitizeRuleResponse(BaseModel):
    id: int | None = None
    name: str
    pattern: str
    mask_strategy: str
    replacement: str | None = None
    is_builtin: bool = False
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ColumnRuleAssign(BaseModel):
    rule_name: str | None = None
