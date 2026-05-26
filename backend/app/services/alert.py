import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import Date, cast, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertRecord, AlertRule, NotificationChannel, alert_rule_channels
from app.models.audit import AuditLog
from app.services.notification import NotificationService


class AlertService:
    """告警服务：规则管理 + 告警检测 + 记录管理"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== 规则 CRUD ==========

    async def list_rules(self) -> list[AlertRule]:
        result = await self.db.execute(
            select(AlertRule).order_by(AlertRule.id.desc())
        )
        return list(result.scalars().all())

    async def get_rule(self, rule_id: int) -> AlertRule | None:
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def create_rule(self, data: dict) -> AlertRule:
        rule = AlertRule(**data)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update_rule(self, rule_id: int, data: dict) -> AlertRule | None:
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        for k, v in data.items():
            if v is not None and hasattr(rule, k):
                setattr(rule, k, v)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: int) -> bool:
        result = await self.db.execute(
            delete(AlertRule).where(AlertRule.id == rule_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========== 告警记录 ==========

    async def list_records(
        self, status: str | None = None, limit: int = 50
    ) -> list[AlertRecord]:
        stmt = select(AlertRecord).order_by(AlertRecord.triggered_at.desc())
        if status:
            stmt = stmt.where(AlertRecord.status == status)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def acknowledge_record(self, record_id: int) -> bool:
        result = await self.db.execute(
            update(AlertRecord)
            .where(AlertRecord.id == record_id, AlertRecord.status == "pending")
            .values(status="acknowledged")
        )
        await self.db.commit()
        return result.rowcount > 0

    async def resolve_record(self, record_id: int) -> bool:
        result = await self.db.execute(
            update(AlertRecord)
            .where(AlertRecord.id == record_id)
            .values(status="resolved", resolved_at=func.now())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def pending_count(self) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(AlertRecord)
            .where(AlertRecord.status == "pending")
        )
        return result.scalar() or 0

    # ========== 告警检测 ==========

    async def check_and_trigger(
        self, action: str, status: str, duration_ms: int | None = None,
        user_id: int | None = None, datasource_id: int | None = None,
    ):
        """在每次请求后调用，检查是否触发告警规则"""
        rules = await self._get_active_rules()
        for rule in rules:
            triggered = await self._evaluate_rule(
                rule, action, status, duration_ms, user_id, datasource_id
            )
            if triggered:
                await self._create_record_if_not_suppressed(rule, triggered)

    async def _get_active_rules(self) -> list[AlertRule]:
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.is_active == True)
        )
        return list(result.scalars().all())

    async def _evaluate_rule(
        self, rule: AlertRule, action: str, status: str,
        duration_ms: int | None, user_id: int | None, datasource_id: int | None,
    ) -> str | None:
        """评估单条规则，返回触发详情或 None"""
        config = json.loads(rule.threshold_config) if rule.threshold_config else {}

        if rule.rule_type == "error_rate":
            return await self._check_error_rate(rule, config)
        elif rule.rule_type == "high_frequency":
            return await self._check_high_frequency(rule, config, user_id)
        elif rule.rule_type == "slow_query":
            return self._check_slow_query(config, duration_ms)
        elif rule.rule_type == "connection_fail":
            # 连接失败：查询失败或连接测试失败或显式连接动作失败
            if status == "error" and (
                "connection" in action.lower()
                or action in ("query_database", "mcp_call:query_database", "datasource_test")
            ):
                return f"数据源连接/查询失败（action={action}）"
        return None

    async def _check_error_rate(self, rule: AlertRule, config: dict) -> str | None:
        window = config.get("window_minutes", 5)
        threshold = config.get("threshold_percent", 50)
        since = datetime.now(timezone.utc) - timedelta(minutes=window)

        total_result = await self.db.execute(
            select(func.count()).select_from(AuditLog)
            .where(AuditLog.created_at >= since)
        )
        total = total_result.scalar() or 0
        if total < 5:
            return None

        error_result = await self.db.execute(
            select(func.count()).select_from(AuditLog)
            .where(AuditLog.created_at >= since, AuditLog.status == "error")
        )
        errors = error_result.scalar() or 0
        rate = errors / total * 100

        if rate >= threshold:
            return f"{window}分钟内失败率 {rate:.1f}%（{errors}/{total}），超过阈值 {threshold}%"
        return None

    async def _check_high_frequency(
        self, rule: AlertRule, config: dict, user_id: int | None
    ) -> str | None:
        window = config.get("window_minutes", 1)
        max_calls = config.get("max_calls", 100)
        since = datetime.now(timezone.utc) - timedelta(minutes=window)

        # 按用户检查
        if rule.scope == "user" and rule.target_id:
            check_user = rule.target_id
        elif user_id:
            check_user = user_id
        else:
            return None

        result = await self.db.execute(
            select(func.count()).select_from(AuditLog)
            .where(
                AuditLog.created_at >= since,
                AuditLog.identity_id == check_user,
            )
        )
        count = result.scalar() or 0
        if count >= max_calls:
            return f"用户 {check_user} 在 {window} 分钟内调用 {count} 次，超过阈值 {max_calls}"
        return None

    def _check_slow_query(self, config: dict, duration_ms: int | None) -> str | None:
        if duration_ms is None:
            return None
        threshold = config.get("threshold_ms", 5000)
        if duration_ms >= threshold:
            return f"查询耗时 {duration_ms}ms，超过阈值 {threshold}ms"
        return None

    async def _create_record_if_not_suppressed(
        self, rule: AlertRule, detail: str
    ):
        """创建告警记录（带抑制检查），并触发通知"""
        suppress_since = datetime.now(timezone.utc) - timedelta(minutes=rule.suppress_minutes)
        existing = await self.db.execute(
            select(func.count()).select_from(AlertRecord)
            .where(
                AlertRecord.rule_id == rule.id,
                AlertRecord.triggered_at >= suppress_since,
            )
        )
        if (existing.scalar() or 0) > 0:
            return

        record = AlertRecord(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            detail=detail,
            status="pending",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        # 查询规则关联的通知渠道并异步发送（失败不影响主流程）
        try:
            await self._notify_channels(rule, record)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("通知渠道发送失败")

    async def _notify_channels(self, rule: AlertRule, record: AlertRecord):
        """查询规则关联的活跃渠道，异步发送通知"""
        result = await self.db.execute(
            select(NotificationChannel)
            .join(alert_rule_channels, NotificationChannel.id == alert_rule_channels.c.channel_id)
            .where(
                alert_rule_channels.c.rule_id == rule.id,
                NotificationChannel.is_active == True,
            )
        )
        channels = list(result.scalars().all())
        if channels:
            service = NotificationService()
            await service.send_alert(record, channels)
