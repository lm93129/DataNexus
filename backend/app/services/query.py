import json
import logging
import time

import sqlglot
from sqlglot import exp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.datasource.pool_manager import pool_manager
from app.services.security import DataDesensitizer, SqlRiskControl

logger = logging.getLogger(__name__)


def _extract_table_names(sql: str, dialect: str | None = None) -> set[str]:
    """从 SQL 中提取所有引用的表名"""
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
        tables = set()
        for stmt in parsed:
            if stmt is None:
                continue
            for table in stmt.find_all(exp.Table):
                if table.name:
                    tables.add(table.name.lower())
        return tables
    except Exception:
        return set()


def _extract_column_names(sql: str, dialect: str | None = None) -> set[str]:
    """从 SQL 中提取所有引用的列名（仅显式列引用）"""
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
        columns = set()
        for stmt in parsed:
            if stmt is None:
                continue
            for col in stmt.find_all(exp.Column):
                if col.name:
                    columns.add(col.name.lower())
        return columns
    except Exception:
        return set()


class QueryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_control = SqlRiskControl(max_rows=settings.max_query_rows)
        self.desensitizer = DataDesensitizer()

    async def execute_query(
        self,
        datasource_id: int,
        sql: str,
        identity_id: int,
        column_rules: dict[str, str] | None = None,
        max_rows_override: int | None = None,
    ) -> dict:
        # 风控校验
        validation = self.risk_control.validate(sql)
        if not validation.is_safe:
            return {"success": False, "error": validation.reason, "data": []}

        # 二次防御：确保 sqlglot 能完整解析 SQL，拒绝无法解析的语句
        try:
            parsed = sqlglot.parse(sql)
            if not parsed or parsed[0] is None:
                return {"success": False, "error": "SQL 解析失败：无法生成有效 AST", "data": []}
        except Exception as e:
            return {"success": False, "error": f"SQL 解析失败：{str(e)}", "data": []}

        # 行数限制（AST级），支持动态覆盖
        effective_max_rows = max_rows_override if max_rows_override is not None else settings.max_query_rows
        sql = self.risk_control.apply_row_limit(sql, effective_max_rows)

        # 执行查询
        try:
            from app.services.datasource import DatasourceService

            ds_service = DatasourceService(self.db)
            ds = await ds_service.get_by_id(datasource_id)
            if not ds:
                return {"success": False, "error": "数据源不存在", "data": []}

            if not ds.is_active:
                return {"success": False, "error": "数据源已停用", "data": []}

            # 黑名单校验：检查 SQL 引用的表和字段是否在黑名单中
            blacklist_error = self._check_blacklist(sql, ds)
            if blacklist_error:
                return {"success": False, "error": blacklist_error, "data": []}

            password = ds_service.get_password(ds)
            engine = await pool_manager.get_engine(ds, password)

            start = time.time()
            async with engine.connect() as conn:
                # 设置语句超时（防止慢查询占用资源）
                timeout_ms = settings.query_timeout_ms
                try:
                    if "postgresql" in str(engine.url):
                        await conn.execute(text(f"SET statement_timeout = {int(timeout_ms)}"))
                    elif "mysql" in str(engine.url):
                        await conn.execute(text(f"SET max_execution_time = {int(timeout_ms)}"))
                except Exception:
                    logger.debug("无法设置 statement_timeout，继续执行")

                result = await conn.execute(text(sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            duration_ms = int((time.time() - start) * 1000)

            # 黑名单列级过滤：从结果集中移除黑名单字段（防止 SELECT * 绕过）
            column_bl = json.loads(ds.column_blacklist or "[]")
            if column_bl:
                from app.services.metadata import _matches_blacklist
                blocked_cols = [c for c in columns if _matches_blacklist(c.lower(), column_bl)]
                if blocked_cols:
                    columns = [c for c in columns if c not in blocked_cols]
                    rows = [{k: v for k, v in row.items() if k not in blocked_cols} for row in rows]

            # 脱敏处理（强制执行：先加载列级规则，再合并调用方传入的规则，最后自动检测）
            loaded_rules = await self._load_column_rules(datasource_id, columns, sql)
            if column_rules:
                loaded_rules.update(column_rules)
            rows = [self.desensitizer.desensitize_row(row, loaded_rules, auto_detect=True) for row in rows]

            return {
                "success": True,
                "data": rows,
                "columns": columns,
                "row_count": len(rows),
                "duration_ms": duration_ms,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "data": []}

    def _check_blacklist(self, sql: str, ds) -> str | None:
        """检查 SQL 是否引用了黑名单中的表或字段"""
        from app.services.metadata import _matches_blacklist

        table_bl = json.loads(ds.table_blacklist or "[]")
        column_bl = json.loads(ds.column_blacklist or "[]")

        if table_bl:
            referenced_tables = _extract_table_names(sql)
            for table_name in referenced_tables:
                if _matches_blacklist(table_name, table_bl):
                    return f"访问被拒绝：表 '{table_name}' 在黑名单中"

        if column_bl:
            referenced_columns = _extract_column_names(sql)
            for col_name in referenced_columns:
                if _matches_blacklist(col_name, column_bl):
                    return f"访问被拒绝：字段 '{col_name}' 在黑名单中"

        return None

    async def _load_column_rules(self, datasource_id: int, columns: list[str], sql: str = "") -> dict[str, str]:
        """从 ColumnMetadata 加载该数据源的列级脱敏规则，优先按表名精确匹配"""
        from sqlalchemy import select
        from app.models.metadata import ColumnMetadata, TableMetadata

        # 尝试从 SQL 提取表名，用于精确匹配
        referenced_tables = _extract_table_names(sql) if sql else set()

        stmt = (
            select(TableMetadata.table_name, ColumnMetadata.column_name, ColumnMetadata.desensitize_rule)
            .join(TableMetadata, ColumnMetadata.table_metadata_id == TableMetadata.id)
            .where(
                TableMetadata.datasource_id == datasource_id,
                ColumnMetadata.column_name.in_(columns),
                ColumnMetadata.desensitize_rule.isnot(None),
            )
        )
        # 如果能确定表名，优先按表名过滤
        if referenced_tables:
            stmt = stmt.where(TableMetadata.table_name.in_(referenced_tables))

        result = await self.db.execute(stmt)
        rules: dict[str, str] = {}
        for row in result:
            # 同名列取第一个匹配的规则（精确表名优先）
            if row.column_name not in rules:
                rules[row.column_name] = row.desensitize_rule
        return rules
