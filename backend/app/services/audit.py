import logging
import re

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

MAX_RETRY = 2


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def sanitize_sql(sql: str) -> str:
        """将 SQL 中的字面量替换为 ? 占位符，防止敏感数据写入审计日志"""
        try:
            import sqlglot
            from sqlglot import exp
            parsed = sqlglot.parse_one(sql)
            for literal in parsed.find_all(exp.Literal):
                literal.replace(exp.Placeholder())
            return parsed.sql()
        except Exception:
            # sqlglot 不可用或解析失败时，用正则替换字符串和数字字面量
            result = re.sub(r"'[^']*'", "'?'", sql)
            result = re.sub(r"\b\d+\b", "?", result)
            return result[:500]

    async def log_safe(
        self,
        identity_id: int | None,
        identity_type: str,
        action: str,
        resource: str,
        request_summary: str | None = None,
        response_summary: str | None = None,
        ip: str | None = None,
        duration_ms: int | None = None,
        status: str = "success",
    ):
        """写审计日志，自动对 SQL 类 request_summary 做字面量脱敏"""
        safe_summary = request_summary
        if request_summary and action in ("query_database", "mcp_call:query_database"):
            safe_summary = self.sanitize_sql(request_summary)

        await self.log(
            identity_id=identity_id,
            identity_type=identity_type,
            action=action,
            resource=resource,
            request_summary=safe_summary,
            response_summary=response_summary,
            ip=ip,
            duration_ms=duration_ms,
            status=status,
        )

    async def log(
        self,
        identity_id: int | None,
        identity_type: str,
        action: str,
        resource: str,
        request_summary: str | None = None,
        response_summary: str | None = None,
        ip: str | None = None,
        duration_ms: int | None = None,
        status: str = "success",
    ):
        entry = AuditLog(
            identity_id=identity_id,
            identity_type=identity_type,
            action=action,
            resource=resource,
            request_summary=request_summary,
            response_summary=response_summary,
            ip=ip,
            duration_ms=duration_ms,
            status=status,
        )
        for attempt in range(MAX_RETRY + 1):
            try:
                new_entry = AuditLog(
                    identity_id=identity_id,
                    identity_type=identity_type,
                    action=action,
                    resource=resource,
                    request_summary=request_summary,
                    response_summary=response_summary,
                    ip=ip,
                    duration_ms=duration_ms,
                    status=status,
                ) if attempt > 0 else entry
                self.db.add(new_entry)
                await self.db.commit()
                return
            except Exception:
                await self.db.rollback()
                if attempt < MAX_RETRY:
                    logger.warning("审计日志写入失败，重试 %s/%s", attempt + 1, MAX_RETRY)
                else:
                    logger.error(
                        "审计日志写入最终失败: action=%s resource=%s",
                        action, resource, exc_info=True,
                    )

    async def query_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        identity_id: int | None = None,
        identity_type: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        request_summary: str | None = None,
        username: str | None = None,
    ) -> dict:
        stmt = (
            select(AuditLog, User.name.label("username"))
            .outerjoin(User, AuditLog.identity_id == User.id)
            .order_by(desc(AuditLog.created_at))
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .outerjoin(User, AuditLog.identity_id == User.id)
        )

        if identity_id is not None:
            stmt = stmt.where(AuditLog.identity_id == identity_id)
            count_stmt = count_stmt.where(AuditLog.identity_id == identity_id)
        if identity_type:
            stmt = stmt.where(AuditLog.identity_type == identity_type)
            count_stmt = count_stmt.where(AuditLog.identity_type == identity_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)
        if resource:
            stmt = stmt.where(AuditLog.resource.ilike(f"%{resource}%"))
            count_stmt = count_stmt.where(AuditLog.resource.ilike(f"%{resource}%"))
        if request_summary:
            stmt = stmt.where(AuditLog.request_summary.ilike(f"%{request_summary}%"))
            count_stmt = count_stmt.where(AuditLog.request_summary.ilike(f"%{request_summary}%"))
        if username:
            stmt = stmt.where(User.name.ilike(f"%{username}%"))
            count_stmt = count_stmt.where(User.name.ilike(f"%{username}%"))

        # 总数
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            log: AuditLog = row[0]
            username: str | None = row.username
            items.append({
                "id": log.id,
                "identity_id": log.identity_id,
                "identity_type": log.identity_type,
                "username": username or (f"user_{log.identity_id}" if log.identity_id else "系统"),
                "action": log.action,
                "resource": log.resource,
                "request_summary": log.request_summary,
                "response_summary": log.response_summary,
                "ip": log.ip,
                "duration_ms": log.duration_ms,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}
