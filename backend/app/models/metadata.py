from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TableMetadata(Base, TimestampMixin):
    __tablename__ = "table_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    datasource_id: Mapped[int] = mapped_column(ForeignKey("datasources.id"))
    table_name: Mapped[str] = mapped_column(String(200))
    table_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class ColumnMetadata(Base, TimestampMixin):
    __tablename__ = "column_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_metadata_id: Mapped[int] = mapped_column(ForeignKey("table_metadata.id"))
    column_name: Mapped[str] = mapped_column(String(200))
    data_type: Mapped[str] = mapped_column(String(100))
    column_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    desensitize_rule: Mapped[str | None] = mapped_column(String(50), nullable=True)
