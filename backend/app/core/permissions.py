"""
RBAC 权限核心模块

权限矩阵定义各角色可执行的操作，格式为 "resource:action"。
通配符 "*" 表示该资源下的所有操作。
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRoleEnum

# 权限矩阵：角色 -> 权限列表
PERMISSION_MATRIX: dict[str, list[str]] = {
    UserRoleEnum.admin.value: [
        "datasource:*",
        "query:*",
        "metadata:*",
        "audit:*",
        "user:*",
        "desensitize:*",
        "custom_api:*",
        "alert:*",
    ],
    UserRoleEnum.analyst.value: [
        "query:execute",
        "metadata:read",
        "audit:read_own",
        "datasource:read",
        "desensitize:read",
        "custom_api:read",
    ],
    UserRoleEnum.viewer.value: [
        "metadata:read",
    ],
}


def _has_permission(role: str, required: str) -> bool:
    """
    检查指定角色是否拥有所需权限。

    :param role: 用户角色字符串，如 "admin"、"analyst"、"viewer"
    :param required: 所需权限，格式为 "resource:action"，如 "query:execute"
    :return: 是否拥有权限
    """
    permissions = PERMISSION_MATRIX.get(role, [])
    resource, action = required.split(":", 1)
    for perm in permissions:
        perm_resource, perm_action = perm.split(":", 1)
        if perm_resource == resource and (perm_action == "*" or perm_action == action):
            return True
    return False


def require_permission(permission: str):
    """
    FastAPI 依赖工厂：要求当前用户拥有指定权限，否则返回 403。

    用法示例：
        @router.get("/foo")
        async def foo(user: User = Depends(require_permission("query:execute"))):
            ...

    :param permission: 所需权限字符串，格式为 "resource:action"
    :return: FastAPI 依赖函数，返回通过鉴权的 User 对象
    """
    from app.api.deps import get_current_user

    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ):
        if not _has_permission(current_user.role, permission):
            # 权限拒绝写审计日志
            from app.core.database import async_session_factory
            from app.services.audit import AuditService
            async with async_session_factory() as db:
                audit = AuditService(db)
                await audit.log(
                    identity_id=current_user.id,
                    identity_type="user",
                    action="permission_denied",
                    resource=permission,
                    request_summary=f"{request.method} {request.url.path}",
                    ip=request.client.host if request.client else None,
                    status="denied",
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要 {permission}",
            )
        return current_user

    return dependency
