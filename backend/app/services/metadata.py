import fnmatch
import json

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.datasource import Datasource
from app.models.metadata import ColumnMetadata, TableMetadata


def _matches_blacklist(name: str, patterns: list[str]) -> bool:
    """检查名称是否匹配黑名单中的任一模式（支持通配符）

    匹配规则：
    - 含通配符（* 或 ?）：使用 fnmatch 模式匹配
    - 不含通配符：精确匹配或前缀匹配（如 "password" 匹配 "password_hash"）
    """
    for pattern in patterns:
        if '*' in pattern or '?' in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
        else:
            if name == pattern or name.startswith(pattern + "_"):
                return True
    return False


class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_blacklists(self, datasource_id: int) -> tuple[list[str], list[str]]:
        """获取数据源的表黑名单和字段黑名单"""
        ds = await self.db.get(Datasource, datasource_id)
        if not ds:
            return [], []
        table_bl = json.loads(ds.table_blacklist or "[]")
        column_bl = json.loads(ds.column_blacklist or "[]")
        return table_bl, column_bl

    async def get_tables(self, datasource_id: int) -> list[TableMetadata]:
        table_bl, _ = await self._get_blacklists(datasource_id)
        stmt = select(TableMetadata).where(
            TableMetadata.datasource_id == datasource_id,
            TableMetadata.is_blocked == False,
        )
        result = await self.db.execute(stmt)
        tables = list(result.scalars().all())
        if table_bl:
            tables = [t for t in tables if not _matches_blacklist(t.table_name, table_bl)]
        return tables

    async def get_columns(self, table_metadata_id: int) -> list[ColumnMetadata]:
        # 获取表所属数据源的字段黑名单
        table = await self.db.get(TableMetadata, table_metadata_id)
        column_bl: list[str] = []
        if table:
            _, column_bl = await self._get_blacklists(table.datasource_id)
        stmt = select(ColumnMetadata).where(
            ColumnMetadata.table_metadata_id == table_metadata_id,
            ColumnMetadata.is_blocked == False,
        )
        result = await self.db.execute(stmt)
        columns = list(result.scalars().all())
        if column_bl:
            columns = [c for c in columns if not _matches_blacklist(c.column_name, column_bl)]
        return columns

    async def get_table_by_name(self, datasource_id: int, table_name: str) -> TableMetadata | None:
        # 先检查黑名单
        table_bl, _ = await self._get_blacklists(datasource_id)
        if table_bl and _matches_blacklist(table_name, table_bl):
            return None
        stmt = select(TableMetadata).where(
            TableMetadata.datasource_id == datasource_id,
            TableMetadata.table_name == table_name,
            TableMetadata.is_blocked == False,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_table_comment(self, table_id: int, comment: str) -> TableMetadata | None:
        """更新表的业务注释"""
        table = await self.db.get(TableMetadata, table_id)
        if not table:
            return None
        table.table_comment = comment
        await self.db.commit()
        await self.db.refresh(table)
        return table

    async def update_column_comment(self, column_id: int, comment: str) -> ColumnMetadata | None:
        """更新字段的业务注释"""
        column = await self.db.get(ColumnMetadata, column_id)
        if not column:
            return None
        column.column_comment = comment
        await self.db.commit()
        await self.db.refresh(column)
        return column

    async def search(self, keyword: str, datasource_id: int | None = None, limit: int = 50) -> dict:
        """搜索表名和列名，返回匹配结果"""
        pattern = f"%{keyword}%"
        # 搜索表
        table_stmt = select(TableMetadata).where(
            TableMetadata.is_blocked == False,
            or_(
                TableMetadata.table_name.ilike(pattern),
                TableMetadata.table_comment.ilike(pattern),
            ),
        )
        if datasource_id:
            table_stmt = table_stmt.where(TableMetadata.datasource_id == datasource_id)
        table_stmt = table_stmt.limit(limit)
        table_result = await self.db.execute(table_stmt)
        tables = table_result.scalars().all()

        # 搜索列
        col_stmt = select(ColumnMetadata).where(
            ColumnMetadata.is_blocked == False,
            or_(
                ColumnMetadata.column_name.ilike(pattern),
                ColumnMetadata.column_comment.ilike(pattern),
            ),
        )
        if datasource_id:
            col_stmt = col_stmt.join(TableMetadata).where(TableMetadata.datasource_id == datasource_id)
        col_stmt = col_stmt.limit(limit)
        col_result = await self.db.execute(col_stmt)
        columns = col_result.scalars().all()

        return {"tables": list(tables), "columns": list(columns)}

    async def sync_from_source(self, datasource_id: int, engine: AsyncEngine, ds_type: str = "postgresql"):
        """从真实数据源同步元数据到平台缓存（表+列）

        根据数据源类型使用不同的元数据采集 SQL。
        """
        tables_sql, columns_sql_fn = self._get_metadata_queries(ds_type)

        async with engine.connect() as conn:
            # 同步表
            tables_result = await conn.execute(text(tables_sql))
            for row in tables_result:
                existing = await self.db.execute(
                    select(TableMetadata).where(
                        TableMetadata.datasource_id == datasource_id,
                        TableMetadata.table_name == row.table_name,
                    )
                )
                table_meta = existing.scalar_one_or_none()
                if not table_meta:
                    table_meta = TableMetadata(
                        datasource_id=datasource_id,
                        table_name=row.table_name,
                    )
                    self.db.add(table_meta)
                    await self.db.flush()

                # 同步该表的列信息
                cols_sql = columns_sql_fn()
                cols_result = await conn.execute(
                    text(cols_sql), {"tbl": row.table_name}
                )
                existing_cols = await self.db.execute(
                    select(ColumnMetadata).where(
                        ColumnMetadata.table_metadata_id == table_meta.id
                    )
                )
                existing_col_names = {c.column_name for c in existing_cols.scalars().all()}

                for col in cols_result:
                    if col.column_name not in existing_col_names:
                        self.db.add(ColumnMetadata(
                            table_metadata_id=table_meta.id,
                            column_name=col.column_name,
                            data_type=col.data_type,
                            column_comment=getattr(col, 'column_comment', None),
                            is_primary_key=getattr(col, 'is_pk', False),
                            is_blocked=False,
                        ))

            await self.db.commit()

    def _get_metadata_queries(self, ds_type: str) -> tuple[str, callable]:
        """根据数据源类型返回表列表 SQL 和列信息 SQL 工厂函数"""
        if ds_type == "postgresql":
            tables_sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
            )
            def columns_fn():
                return (
                    "SELECT c.column_name, c.data_type, "
                    "col_description(cls.oid, c.ordinal_position) as column_comment, "
                    "CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_pk "
                    "FROM information_schema.columns c "
                    "JOIN pg_class cls ON cls.relname = c.table_name "
                    "JOIN pg_namespace ns ON ns.oid = cls.relnamespace AND ns.nspname = c.table_schema "
                    "LEFT JOIN ("
                    "  SELECT ku.column_name, ku.table_name "
                    "  FROM information_schema.table_constraints tc "
                    "  JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name "
                    "  WHERE tc.constraint_type = 'PRIMARY KEY'"
                    ") pk ON pk.column_name = c.column_name AND pk.table_name = c.table_name "
                    "WHERE c.table_schema = current_schema() AND c.table_name = :tbl "
                    "ORDER BY c.ordinal_position"
                )
        elif ds_type == "mysql":
            tables_sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
            )
            def columns_fn():
                return (
                    "SELECT c.column_name, c.data_type, "
                    "c.column_comment, "
                    "CASE WHEN c.column_key = 'PRI' THEN true ELSE false END as is_pk "
                    "FROM information_schema.columns c "
                    "WHERE c.table_schema = DATABASE() AND c.table_name = :tbl "
                    "ORDER BY c.ordinal_position"
                )
        elif ds_type == "mssql":
            tables_sql = (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'dbo' AND table_type = 'BASE TABLE'"
            )
            def columns_fn():
                return (
                    "SELECT c.column_name, c.data_type, "
                    "CAST(ep.value AS NVARCHAR(500)) as column_comment, "
                    "CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk "
                    "FROM information_schema.columns c "
                    "LEFT JOIN sys.extended_properties ep "
                    "  ON ep.major_id = OBJECT_ID(c.table_schema + '.' + c.table_name) "
                    "  AND ep.minor_id = c.ordinal_position AND ep.name = 'MS_Description' "
                    "LEFT JOIN ("
                    "  SELECT ku.column_name, ku.table_name "
                    "  FROM information_schema.table_constraints tc "
                    "  JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name "
                    "  WHERE tc.constraint_type = 'PRIMARY KEY'"
                    ") pk ON pk.column_name = c.column_name AND pk.table_name = c.table_name "
                    "WHERE c.table_schema = 'dbo' AND c.table_name = :tbl "
                    "ORDER BY c.ordinal_position"
                )
        elif ds_type == "oracle":
            tables_sql = (
                "SELECT table_name FROM user_tables"
            )
            def columns_fn():
                return (
                    "SELECT c.column_name, c.data_type, "
                    "cc.comments as column_comment, "
                    "CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk "
                    "FROM user_tab_columns c "
                    "LEFT JOIN user_col_comments cc "
                    "  ON cc.table_name = c.table_name AND cc.column_name = c.column_name "
                    "LEFT JOIN ("
                    "  SELECT cols.column_name, cols.table_name "
                    "  FROM user_constraints cons "
                    "  JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name "
                    "  WHERE cons.constraint_type = 'P'"
                    ") pk ON pk.column_name = c.column_name AND pk.table_name = c.table_name "
                    "WHERE c.table_name = :tbl "
                    "ORDER BY c.column_id"
                )
        else:
            raise ValueError(f"不支持的数据源类型: {ds_type}")

        return tables_sql, columns_fn
