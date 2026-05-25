from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    identity_type: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(50))
    resource: Mapped[str] = mapped_column(String(200))
    request_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # success/error
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
