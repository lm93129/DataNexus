from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["审计日志"])


@router.get("/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity_id: int | None = None,
    action: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    # analyst 角色只能查看自己的审计日志，不能查看其他用户的
    from app.models.user import UserRoleEnum
    if user.role == UserRoleEnum.analyst.value:
        identity_id = user.id

    service = AuditService(db)
    return await service.query_logs(
        page=page, page_size=page_size, identity_id=identity_id, action=action
    )
