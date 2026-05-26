from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.audit import AuditService
from app.services.query import QueryService
from app.services.query_history import QueryHistoryService
from app.services.rate_limit import RateLimitService
from app.services.sql_suggest import SqlSuggestionService
from app.services.alert import AlertService

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    datasource_id: int
    sql: str = Field(..., max_length=10000, description="SQL 查询语句")


class SuggestRequest(BaseModel):
    datasource_id: int
    sql: str = Field(..., max_length=10000, description="SQL 查询语句")
    error_msg: str = Field(default="", max_length=2000, description="数据库返回的错误信息")


router = APIRouter(prefix="/query", tags=["数据查询"])


@router.post("/execute")
@limiter.limit("30/minute")
async def execute_query(
    request: Request,
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("query:execute")),
):
    # 动态限流检查
    rl_service = RateLimitService(db)
    deny_reason = await rl_service.check_rate_limit(
        user_id=user.id, datasource_id=body.datasource_id
    )
    if deny_reason:
        raise HTTPException(status_code=429, detail=deny_reason)

    # 获取动态最大行数限制
    dynamic_max_rows = await rl_service.get_max_rows(
        user_id=user.id, datasource_id=body.datasource_id
    )

    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=body.datasource_id,
        sql=body.sql,
        identity_id=user.id,
        max_rows_override=dynamic_max_rows,
    )

    # 查询失败时自动生成纠错建议
    if not result["success"]:
        try:
            suggest_service = SqlSuggestionService(db)
            suggestions = await suggest_service.get_suggestions(
                sql=body.sql,
                datasource_id=body.datasource_id,
                error_msg=result.get("error", ""),
            )
            if suggestions:
                result["suggestions"] = suggestions
        except Exception:
            logger.exception("生成 SQL 纠错建议失败")

    # 记录请求到限流计数器
    await rl_service.record_request(user_id=user.id, datasource_id=body.datasource_id)

    # 保存查询历史（失败不阻塞响应）
    try:
        history_service = QueryHistoryService(db)
        await history_service.save(
            user_id=user.id,
            datasource_id=body.datasource_id,
            sql=body.sql,
            status="success" if result["success"] else "error",
            duration_ms=result.get("duration_ms"),
            row_count=result.get("row_count"),
        )
    except Exception:
        logger.exception("保存查询历史失败")
        await db.rollback()

    # 审计日志
    audit = AuditService(db)
    await audit.log_safe(
        identity_id=user.id,
        identity_type="user",
        action="query_database",
        resource=f"datasource:{body.datasource_id}",
        request_summary=body.sql,
        response_summary=f"{result.get('row_count', 0)} rows",
        ip=request.client.host if request.client else None,
        duration_ms=result.get("duration_ms"),
        status="success" if result["success"] else "error",
    )

    # 异步告警检测（不阻塞响应）
    try:
        alert_service = AlertService(db)
        await alert_service.check_and_trigger(
            action="query_database",
            status="success" if result["success"] else "error",
            duration_ms=result.get("duration_ms"),
            user_id=user.id,
            datasource_id=body.datasource_id,
        )
    except Exception:
        logger.exception("告警检测失败")

    return result


@router.get("/history")
@limiter.limit("60/minute")
async def get_query_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("query:execute")),
):
    service = QueryHistoryService(db)
    entries = await service.list_by_user(user.id)
    return [
        {
            "id": e.id,
            "datasource_id": e.datasource_id,
            "sql": e.sql,
            "status": e.status,
            "duration_ms": e.duration_ms,
            "row_count": e.row_count,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.delete("/history/{history_id}", status_code=204)
async def delete_query_history(
    history_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("query:execute")),
):
    service = QueryHistoryService(db)
    deleted = await service.delete(history_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")


@router.post("/export")
@limiter.limit("10/minute")
async def export_query_csv(
    request: Request,
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("query:execute")),
):
    """执行查询并以 CSV 格式流式返回结果"""
    import csv
    import io

    # 动态限流检查
    rl_service = RateLimitService(db)
    deny_reason = await rl_service.check_rate_limit(
        user_id=user.id, datasource_id=body.datasource_id
    )
    if deny_reason:
        raise HTTPException(status_code=429, detail=deny_reason)

    dynamic_max_rows = await rl_service.get_max_rows(
        user_id=user.id, datasource_id=body.datasource_id
    )

    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=body.datasource_id,
        sql=body.sql,
        identity_id=user.id,
        max_rows_override=dynamic_max_rows,
    )

    # 记录请求到限流计数器
    await rl_service.record_request(user_id=user.id, datasource_id=body.datasource_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "查询失败"))

    columns = result.get("columns", [])
    data = result.get("data", [])

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        output.seek(0)
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)
        for row in data:
            writer.writerow([v if (v := row.get(c)) is not None else "" for c in columns])
            output.seek(0)
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=query_result.csv"},
    )


@router.post("/suggest")
async def get_sql_suggestions(
    body: SuggestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("query:execute")),
):
    """SQL 智能纠错：语法检查 + 表名/字段名模糊匹配"""
    service = SqlSuggestionService(db)
    suggestions = await service.get_suggestions(
        sql=body.sql,
        datasource_id=body.datasource_id,
        error_msg=body.error_msg,
    )
    return {"suggestions": suggestions}
