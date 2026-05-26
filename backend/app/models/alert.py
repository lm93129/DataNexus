from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AlertRule(Base, TimestampMixin):
    """告警规则"""
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # 规则类型: error_rate / high_frequency / slow_query / connection_fail
    rule_type: Mapped[str] = mapped_column(String(30))
    # 阈值配置（JSON 字符串）
    # error_rate: {"window_minutes": 5, "threshold_percent": 50}
    # high_frequency: {"window_minutes": 1, "max_calls": 100}
    # slow_query: {"threshold_ms": 5000}
    # connection_fail: {"consecutive": 3}
    threshold_config: Mapped[str] = mapped_column(Text, default="{}")
    # 作用范围: global / user / datasource
    scope: Mapped[str] = mapped_column(String(20), default="global")
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 告警抑制：同规则 N 分钟内不重复触发
    suppress_minutes: Mapped[int] = mapped_column(Integer, default=10)


class AlertRecord(Base):
    """告警记录"""
    __tablename__ = "alert_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(Integer, index=True)
    rule_name: Mapped[str] = mapped_column(String(100))
    rule_type: Mapped[str] = mapped_column(String(30))
    # 触发详情
    detail: Mapped[str] = mapped_column(Text, default="")
    # 处理状态: pending / acknowledged / resolved
    status: Mapped[str] = mapped_column(String(20), default="pending")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
