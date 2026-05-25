from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class QueryHistory(Base, TimestampMixin):
    __tablename__ = "query_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    datasource_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasources.id"))
    sql: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))  # success/error
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
