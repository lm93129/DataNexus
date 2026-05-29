import fnmatch
import json

from typing import Union

from sqlalchemy import Engine, or_, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.datasource.pool_manager import async_connect
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


def _metadata_cell(row, field_name: str):
    """按平台内部约定读取元数据字段，不承担业务默认值兜底。

    SQLAlchemy 暴露的行键由底层数据库驱动决定；MySQL 的 information_schema
    会把未显式稳定的键暴露为大写，统一在采集边界兼容大小写，避免内部同步流程
    散落重复判断。
    """
    row_mapping = row._mapping
    candidates = (field_name, field_name.upper(), field_name.lower())
    for candidate in candidates:
        if candidate in row_mapping:
            return row_mapping[candidate]
    available_fields = ", ".join(str(key) for key in row_mapping.keys())
    raise KeyError(f"元数据字段缺失: {field_name}; 可用字段: {available_fields}")


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

    async def sync_from_source(self, datasource_id: int, engine: Union[AsyncEngine, Engine], ds_type: str = "postgresql"):
        """从真实数据源同步元数据到平台缓存（表+列）

        根据数据源类型使用不同的元数据采集 SQL。
        """
        tables_sql, columns_sql_fn = self._get_metadata_queries(ds_type)

        async with async_connect(engine) as conn:
            # 同步表
            tables_result = await conn.execute(text(tables_sql))
            for row in tables_result:
                table_name = _metadata_cell(row, "table_name")
                table_comment = _metadata_cell(row, "table_comment")
                existing = await self.db.execute(
                    select(TableMetadata).where(
                        TableMetadata.datasource_id == datasource_id,
                        TableMetadata.table_name == table_name,
                    )
                )
                table_meta = existing.scalar_one_or_none()
                if not table_meta:
                    table_meta = TableMetadata(
                        datasource_id=datasource_id,
                        table_name=table_name,
                        table_comment=table_comment,
                    )
                    self.db.add(table_meta)
                    await self.db.flush()
                else:
                    comment = table_comment
                    if comment and table_meta.table_comment != comment:
                        table_meta.table_comment = comment

                # 同步该表的列信息
                cols_sql = columns_sql_fn()
                cols_result = await conn.execute(
                    text(cols_sql), {"tbl": table_name}
                )
                existing_cols = await self.db.execute(
                    select(ColumnMetadata).where(
                        ColumnMetadata.table_metadata_id == table_meta.id
                    )
                )
                existing_col_names = {c.column_name for c in existing_cols.scalars().all()}

                for col in cols_result:
                    column_name = _metadata_cell(col, "column_name")
                    if column_name not in existing_col_names:
                        self.db.add(ColumnMetadata(
                            table_metadata_id=table_meta.id,
                            column_name=column_name,
                            data_type=_metadata_cell(col, "data_type"),
                            column_comment=_metadata_cell(col, "column_comment"),
                            is_primary_key=bool(_metadata_cell(col, "is_pk")),
                            is_blocked=False,
                        ))

            await self.db.commit()

    def _get_metadata_queries(self, ds_type: str) -> tuple[str, callable]:
        """根据数据源类型返回表列表 SQL 和列信息 SQL 工厂函数"""
        if ds_type == "postgresql":
            tables_sql = (
                "SELECT t.table_name, "
                "obj_description(cls.oid) as table_comment "
                "FROM information_schema.tables t "
                "JOIN pg_class cls ON cls.relname = t.table_name "
                "JOIN pg_namespace ns ON ns.oid = cls.relnamespace AND ns.nspname = t.table_schema "
                "WHERE t.table_schema = current_schema() AND t.table_type = 'BASE TABLE'"
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
                "SELECT t.table_name, t.table_comment "
                "FROM information_schema.tables t "
                "WHERE t.table_schema = DATABASE() AND t.table_type = 'BASE TABLE'"
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
                "SELECT t.table_name, "
                "CAST(ep.value AS NVARCHAR(500)) as table_comment "
                "FROM information_schema.tables t "
                "LEFT JOIN sys.extended_properties ep "
                "  ON ep.major_id = OBJECT_ID(t.table_schema + '.' + t.table_name) "
                "  AND ep.minor_id = 0 AND ep.name = 'MS_Description' "
                "WHERE t.table_schema = 'dbo' AND t.table_type = 'BASE TABLE'"
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
                "SELECT t.table_name, c.comments as table_comment "
                "FROM user_tables t "
                "LEFT JOIN user_tab_comments c ON c.table_name = t.table_name"
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
