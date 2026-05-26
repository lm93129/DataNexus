from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import _has_permission
from app.models.user import User
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["审计日志"])


def _require_audit_read():
    """审计日志读取权限依赖：接受 audit:read（全量）或 audit:read_own（仅本人）"""
    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ):
        has_full = _has_permission(current_user.role, "audit:read")
        has_own = _has_permission(current_user.role, "audit:read_own")
        if not has_full and not has_own:
            from app.core.database import async_session_factory
            from app.services.audit import AuditService as _Audit
            async with async_session_factory() as db:
                audit = _Audit(db)
                await audit.log(
                    identity_id=current_user.id,
                    identity_type="user",
                    action="permission_denied",
                    resource="audit:read",
                    request_summary=f"{request.method} {request.url.path}",
                    ip=request.client.host if request.client else None,
                    status="denied",
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足：需要 audit:read 或 audit:read_own",
            )
        return current_user
    return dependency


@router.get("/logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity_id: int | None = None,
    action: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_audit_read()),
):
    # 仅拥有 audit:read_own 的用户只能查看自己的审计日志
    if not _has_permission(user.role, "audit:read"):
        identity_id = user.id

    service = AuditService(db)
    return await service.query_logs(
        page=page, page_size=page_size, identity_id=identity_id, action=action
    )
