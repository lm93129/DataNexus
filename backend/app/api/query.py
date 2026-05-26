from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

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


class QueryRequest(BaseModel):
    datasource_id: int
    sql: str


class SuggestRequest(BaseModel):
    datasource_id: int
    sql: str
    error_msg: str = Field(default="", description="数据库返回的错误信息")


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

    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=body.datasource_id,
        sql=body.sql,
        identity_id=user.id,
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
            pass

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
        pass

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
    """执行查询并以 CSV 格式返回结果"""
    import csv
    import io

    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=body.datasource_id,
        sql=body.sql,
        identity_id=user.id,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "查询失败"))

    output = io.StringIO()
    writer = csv.writer(output)
    columns = result.get("columns", [])
    writer.writerow(columns)
    for row in result.get("data", []):
        writer.writerow([row.get(c, "") for c in columns])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
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
