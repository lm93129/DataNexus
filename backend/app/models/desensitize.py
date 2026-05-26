from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DesensitizeRule(Base, TimestampMixin):
    __tablename__ = "desensitize_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    pattern: Mapped[str] = mapped_column(Text)
    mask_strategy: Mapped[str] = mapped_column(String(50))
    replacement: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)


class RateLimit(Base, TimestampMixin):
    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(20), default="global")  # global/user/datasource/api
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 对应 scope 的具体 ID
    max_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_per_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rows_per_query: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
