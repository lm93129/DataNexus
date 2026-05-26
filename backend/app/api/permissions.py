from fastapi import APIRouter, Depends

from app.core.permissions import PERMISSION_MATRIX, require_permission
from app.models.user import User

router = APIRouter(prefix="/permissions", tags=["权限管理"])


@router.get("/matrix")
async def get_permission_matrix(
    user: User = Depends(require_permission("user:read")),
):
    """获取 RBAC 权限矩阵（只读）"""
    # 从矩阵中提取所有资源名
    resources: set[str] = set()
    for perms in PERMISSION_MATRIX.values():
        for perm in perms:
            resource, _ = perm.split(":", 1)
            resources.add(resource)

    return {
        "roles": list(PERMISSION_MATRIX.keys()),
        "resources": sorted(resources),
        "matrix": PERMISSION_MATRIX,
    }
