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
    identity_id: Mapped[int] = mapped_column(Integer)
    max_qps: Mapped[int] = mapped_column(Integer, default=10)
    max_daily_calls: Mapped[int] = mapped_column(Integer, default=10000)
    max_rows_per_query: Mapped[int] = mapped_column(Integer, default=1000)
