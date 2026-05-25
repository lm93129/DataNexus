from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.audit import AuditLog
from app.models.datasource import Datasource
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()

    # 数据源总数
    ds_count = await db.execute(select(func.count()).select_from(Datasource))
    datasource_count = ds_count.scalar() or 0

    # 今日查询数
    query_count_result = await db.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.action.in_(["query_database", "mcp_call:query_database"]),
            cast(AuditLog.created_at, Date) == today,
        )
    )
    query_count_today = query_count_result.scalar() or 0

    # 活跃用户数
    active_result = await db.execute(
        select(func.count(func.distinct(AuditLog.identity_id)))
        .select_from(AuditLog)
        .where(cast(AuditLog.created_at, Date) == today)
    )
    active_users = active_result.scalar() or 0

    # 错误率
    total_today_result = await db.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(cast(AuditLog.created_at, Date) == today)
    )
    total_today = total_today_result.scalar() or 0

    error_today_result = await db.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(
            cast(AuditLog.created_at, Date) == today,
            AuditLog.status == "error",
        )
    )
    error_today = error_today_result.scalar() or 0
    error_rate = round((error_today / total_today * 100), 1) if total_today > 0 else 0

    return {
        "datasource_count": datasource_count,
        "query_count_today": query_count_today,
        "active_users": active_users,
        "error_rate": error_rate,
    }


@router.get("/query-trend")
async def get_query_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = []
    for i in range(days - 1, -1, -1):
        day = date.today() - timedelta(days=i)
        count_result = await db.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action.in_(["query_database", "mcp_call:query_database"]),
                cast(AuditLog.created_at, Date) == day,
            )
        )
        results.append({"time": day.isoformat(), "count": count_result.scalar() or 0})

    return results
