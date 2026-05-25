from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query_history import QueryHistory


class QueryHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, user_id: int, datasource_id: int, sql: str, status: str, duration_ms: int | None = None, row_count: int | None = None) -> QueryHistory:
        entry = QueryHistory(
            user_id=user_id,
            datasource_id=datasource_id,
            sql=sql,
            status=status,
            duration_ms=duration_ms,
            row_count=row_count,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[QueryHistory]:
        result = await self.db.execute(
            select(QueryHistory)
            .where(QueryHistory.user_id == user_id)
            .order_by(desc(QueryHistory.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, history_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(QueryHistory).where(QueryHistory.id == history_id, QueryHistory.user_id == user_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.commit()
        return True
