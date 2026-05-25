from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.metadata import ColumnMetadata, TableMetadata


class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tables(self, datasource_id: int) -> list[TableMetadata]:
        stmt = select(TableMetadata).where(
            TableMetadata.datasource_id == datasource_id,
            TableMetadata.is_blocked == False,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_columns(self, table_metadata_id: int) -> list[ColumnMetadata]:
        stmt = select(ColumnMetadata).where(
            ColumnMetadata.table_metadata_id == table_metadata_id,
            ColumnMetadata.is_blocked == False,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_table_by_name(self, datasource_id: int, table_name: str) -> TableMetadata | None:
        stmt = select(TableMetadata).where(
            TableMetadata.datasource_id == datasource_id,
            TableMetadata.table_name == table_name,
            TableMetadata.is_blocked == False,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def sync_from_source(self, datasource_id: int, engine: AsyncEngine):
        """从真实数据源同步元数据到平台缓存（表+列）"""
        async with engine.connect() as conn:
            # 同步表
            tables_result = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
                )
            )
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
                cols_result = await conn.execute(
                    text(
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
                    ),
                    {"tbl": row.table_name},
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
                            column_comment=col.column_comment,
                            is_primary_key=col.is_pk,
                            is_blocked=False,
                        ))

            await self.db.commit()
