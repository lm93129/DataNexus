from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.audit import AuditService
from app.services.query import QueryService


class QueryRequest(BaseModel):
    datasource_id: int
    sql: str


router = APIRouter(prefix="/query", tags=["数据查询"])


@router.post("/execute")
@limiter.limit("30/minute")
async def execute_query(
    request: Request,
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("query:execute")),
):
    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=body.datasource_id,
        sql=body.sql,
        identity_id=user.id,  # 使用 User 对象的 id 属性，而非 payload dict
    )

    # 审计日志（使用 log_safe 自动对 SQL 字面量脱敏）
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

    return result
