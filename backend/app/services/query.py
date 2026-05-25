import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.datasource.pool_manager import pool_manager
from app.services.security import DataDesensitizer, SqlRiskControl


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
    ) -> dict:
        # 风控校验
        validation = self.risk_control.validate(sql)
        if not validation.is_safe:
            return {"success": False, "error": validation.reason, "data": []}

        # 行数限制（AST级）
        sql = self.risk_control.apply_row_limit(sql, settings.max_query_rows)

        # 执行查询
        try:
            from app.services.datasource import DatasourceService

            ds_service = DatasourceService(self.db)
            ds = await ds_service.get_by_id(datasource_id)
            if not ds:
                return {"success": False, "error": "数据源不存在", "data": []}

            if not ds.is_active:
                return {"success": False, "error": "数据源已停用", "data": []}

            password = ds_service.get_password(ds)
            engine = await pool_manager.get_engine(ds, password)

            start = time.time()
            async with engine.connect() as conn:
                result = await conn.execute(text(sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            duration_ms = int((time.time() - start) * 1000)

            # 脱敏处理（强制执行：先加载列级规则，再合并调用方传入的规则，最后自动检测）
            loaded_rules = await self._load_column_rules(datasource_id, columns)
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

    async def _load_column_rules(self, datasource_id: int, columns: list[str]) -> dict[str, str]:
        """从 ColumnMetadata 加载该数据源的列级脱敏规则"""
        from sqlalchemy import select
        from app.models.metadata import ColumnMetadata, TableMetadata

        stmt = (
            select(ColumnMetadata.column_name, ColumnMetadata.desensitize_rule)
            .join(TableMetadata, ColumnMetadata.table_metadata_id == TableMetadata.id)
            .where(
                TableMetadata.datasource_id == datasource_id,
                ColumnMetadata.column_name.in_(columns),
                ColumnMetadata.desensitize_rule.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        return {row.column_name: row.desensitize_rule for row in result}
