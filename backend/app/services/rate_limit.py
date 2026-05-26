import time
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.desensitize import RateLimit

# 内存计数器：key = (scope, target_id, user_id), value = [(timestamp, ...)]
_counters: dict[str, list[float]] = defaultdict(list)


def _counter_key(scope: str, target_id: int | None, user_id: int) -> str:
    """生成计数器 key，按 scope 决定维度：
    - global: 全局共享计数
    - datasource: 按数据源计数（不绑定用户）
    - user: 按用户计数
    - api: 按 API 计数（不绑定用户）
    """
    if scope == "user":
        return f"{scope}:{target_id or user_id}:{user_id}"
    elif scope == "datasource":
        return f"{scope}:{target_id or 0}:all"
    elif scope == "api":
        return f"{scope}:{target_id or 0}:all"
    else:  # global
        return f"global:0:all"


def _clean_window(timestamps: list[float], window_seconds: int) -> list[float]:
    """清理超出时间窗口的记录"""
    cutoff = time.time() - window_seconds
    return [t for t in timestamps if t > cutoff]


class RateLimitService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rules(self) -> list[RateLimit]:
        result = await self.db.execute(
            select(RateLimit).order_by(RateLimit.id)
        )
        return list(result.scalars().all())

    async def get_rule(self, rule_id: int) -> RateLimit | None:
        return await self.db.get(RateLimit, rule_id)

    async def create_rule(self, data: dict) -> RateLimit:
        rule = RateLimit(**data)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update_rule(self, rule_id: int, data: dict) -> RateLimit | None:
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(rule, key, value)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: int) -> bool:
        rule = await self.get_rule(rule_id)
        if not rule:
            return False
        await self.db.delete(rule)
        await self.db.commit()
        return True

    async def check_rate_limit(
        self, user_id: int, datasource_id: int | None = None, api_id: int | None = None
    ) -> str | None:
        """
        检查是否超限。返回 None 表示通过，返回字符串表示超限原因。
        优先级：具体规则 > 全局规则
        """
        result = await self.db.execute(
            select(RateLimit).where(RateLimit.is_active == True)
        )
        rules = list(result.scalars().all())

        now = time.time()

        for rule in rules:
            # 确定规则是否适用于当前请求
            if rule.scope == "user" and rule.target_id != user_id:
                continue
            if rule.scope == "datasource" and rule.target_id != datasource_id:
                continue
            if rule.scope == "api" and rule.target_id != api_id:
                continue

            key = _counter_key(rule.scope, rule.target_id, user_id)

            # 检查每分钟限制
            if rule.max_per_minute:
                timestamps = _clean_window(_counters[key + ":min"], 60)
                _counters[key + ":min"] = timestamps
                if len(timestamps) >= rule.max_per_minute:
                    return f"超出限流规则「{rule.name}」：每分钟最多 {rule.max_per_minute} 次请求"

            # 检查每小时限制
            if rule.max_per_hour:
                timestamps = _clean_window(_counters[key + ":hour"], 3600)
                _counters[key + ":hour"] = timestamps
                if len(timestamps) >= rule.max_per_hour:
                    return f"超出限流规则「{rule.name}」：每小时最多 {rule.max_per_hour} 次请求"

            # 检查每日限制
            if rule.max_per_day:
                timestamps = _clean_window(_counters[key + ":day"], 86400)
                _counters[key + ":day"] = timestamps
                if len(timestamps) >= rule.max_per_day:
                    return f"超出限流规则「{rule.name}」：每日最多 {rule.max_per_day} 次请求"

        return None

    async def record_request(
        self, user_id: int, datasource_id: int | None = None, api_id: int | None = None
    ):
        """记录一次请求到计数器"""
        result = await self.db.execute(
            select(RateLimit).where(RateLimit.is_active == True)
        )
        rules = list(result.scalars().all())
        now = time.time()

        for rule in rules:
            if rule.scope == "user" and rule.target_id != user_id:
                continue
            if rule.scope == "datasource" and rule.target_id != datasource_id:
                continue
            if rule.scope == "api" and rule.target_id != api_id:
                continue
            if rule.scope == "global" or (
                (rule.scope == "user" and rule.target_id == user_id) or
                (rule.scope == "datasource" and rule.target_id == datasource_id) or
                (rule.scope == "api" and rule.target_id == api_id)
            ):
                key = _counter_key(rule.scope, rule.target_id, user_id)
                _counters[key + ":min"].append(now)
                _counters[key + ":hour"].append(now)
                _counters[key + ":day"].append(now)

    async def get_max_rows(
        self, user_id: int, datasource_id: int | None = None
    ) -> int | None:
        """获取适用的最大行数限制（取最小值）"""
        result = await self.db.execute(
            select(RateLimit).where(RateLimit.is_active == True)
        )
        rules = list(result.scalars().all())
        max_rows = None

        for rule in rules:
            if rule.max_rows_per_query is None:
                continue
            if rule.scope == "global":
                max_rows = min(max_rows, rule.max_rows_per_query) if max_rows else rule.max_rows_per_query
            elif rule.scope == "user" and rule.target_id == user_id:
                max_rows = min(max_rows, rule.max_rows_per_query) if max_rows else rule.max_rows_per_query
            elif rule.scope == "datasource" and rule.target_id == datasource_id:
                max_rows = min(max_rows, rule.max_rows_per_query) if max_rows else rule.max_rows_per_query

        return max_rows
