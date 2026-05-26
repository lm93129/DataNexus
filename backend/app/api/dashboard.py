from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select, text
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
    today = datetime.now(timezone.utc).date()

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
        day = datetime.now(timezone.utc).date() - timedelta(days=i)
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


@router.get("/hourly-trend")
async def get_hourly_trend(
    hours: int = Query(24, ge=1, le=72),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按小时聚合的调用趋势"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        text("""
            SELECT date_trunc('hour', created_at) as hour, count(*) as cnt
            FROM audit_logs
            WHERE created_at >= :since
              AND action IN ('query_database', 'mcp_call:query_database')
            GROUP BY hour ORDER BY hour
        """),
        {"since": since},
    )
    return [{"time": row[0].isoformat(), "count": row[1]} for row in result.fetchall()]


@router.get("/top-users")
async def get_top_users(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按用户调用量 Top N"""
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    result = await db.execute(
        text("""
            SELECT a.identity_id, u.name as username, count(*) as cnt
            FROM audit_logs a
            LEFT JOIN users u ON u.id = a.identity_id
            WHERE a.created_at >= :since AND a.identity_type = 'user'
            GROUP BY a.identity_id, u.name
            ORDER BY cnt DESC LIMIT :lim
        """),
        {"since": since, "lim": limit},
    )
    return [{"user_id": row[0], "username": row[1] or f"user_{row[0]}", "count": row[2]} for row in result.fetchall()]


@router.get("/top-datasources")
async def get_top_datasources(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按数据源调用量 Top N"""
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    result = await db.execute(
        text("""
            SELECT resource, count(*) as cnt
            FROM audit_logs
            WHERE created_at >= :since
              AND action IN ('query_database', 'mcp_call:query_database')
              AND resource LIKE 'datasource:%'
            GROUP BY resource ORDER BY cnt DESC LIMIT :lim
        """),
        {"since": since, "lim": limit},
    )
    return [{"datasource": row[0], "count": row[1]} for row in result.fetchall()]


@router.get("/slow-queries")
async def get_slow_queries(
    threshold_ms: int = Query(1000, ge=100),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """慢查询排行"""
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.created_at >= since,
            AuditLog.action.in_(["query_database", "mcp_call:query_database"]),
            AuditLog.duration_ms != None,
            AuditLog.duration_ms >= threshold_ms,
        )
        .order_by(AuditLog.duration_ms.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "identity_id": r.identity_id,
            "resource": r.resource,
            "sql": r.request_summary[:200] if r.request_summary else None,
            "duration_ms": r.duration_ms,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/error-stats")
async def get_error_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """错误率统计：按天的成功/失败数"""
    results = []
    for i in range(days - 1, -1, -1):
        day = datetime.now(timezone.utc).date() - timedelta(days=i)
        total_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(cast(AuditLog.created_at, Date) == day)
        )
        error_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(
                cast(AuditLog.created_at, Date) == day, AuditLog.status == "error"
            )
        )
        total = total_result.scalar() or 0
        errors = error_result.scalar() or 0
        results.append({
            "date": day.isoformat(),
            "total": total,
            "errors": errors,
            "success": total - errors,
            "error_rate": round(errors / total * 100, 1) if total > 0 else 0,
        })
    return results
