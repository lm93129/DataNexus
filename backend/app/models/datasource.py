from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Datasource(Base, TimestampMixin):
    __tablename__ = "datasources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    type: Mapped[str] = mapped_column(String(20))  # mysql/postgresql/mssql/oracle
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    database: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100))
    encrypted_password: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 黑名单：JSON 数组字符串，如 ["sys_*", "tmp_*"]
    table_blacklist: Mapped[str | None] = mapped_column(Text, nullable=True, default="[]")
    column_blacklist: Mapped[str | None] = mapped_column(Text, nullable=True, default="[]")
