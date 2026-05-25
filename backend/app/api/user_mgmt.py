import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.core.security import decrypt_api_key, encrypt_api_key, hash_api_key, hash_password, verify_password
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse, UserUpdate
from app.services.audit import AuditService

router = APIRouter(prefix="/users", tags=["用户管理"])


def _to_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        username=u.name,
        role=u.role,
        is_active=u.is_active,
        has_api_key=bool(u.api_key_hash),
        created_at=u.created_at.isoformat() if u.created_at else None,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:read")),
):
    result = await db.execute(select(User).where(User.identity_type == "user"))
    return [_to_response(u) for u in result.scalars().all()]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:create")),
):
    existing = await db.execute(select(User).where(User.name == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    new_user = User(
        name=data.username,
        identity_type="user",
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="user_create",
        resource=f"user:{new_user.id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return _to_response(new_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:update")),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.role is not None:
        target.role = data.role
    if data.is_active is not None:
        target.is_active = data.is_active
    if data.reset_password is not None:
        target.password_hash = hash_password(data.reset_password)
    await db.commit()
    await db.refresh(target)

    audit = AuditService(db)
    await audit.log_safe(
        identity_id=user.id,
        identity_type="user",
        action="user_update",
        resource=f"user:{user_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return _to_response(target)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:delete")),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(target)
    await db.commit()

    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="user_delete",
        resource=f"user:{user_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(data.old_password, user.password_hash or ""):
        raise HTTPException(status_code=400, detail="当前密码错误")
    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "密码修改成功"}


@router.post("/{user_id}/api-key")
async def generate_user_api_key(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:update")),
):
    """管理员为指定用户生成 API Key"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    raw_key = f"dnx_{secrets.token_urlsafe(32)}"
    target.api_key_hash = hash_api_key(raw_key)
    target.api_key_encrypted = encrypt_api_key(raw_key)
    await db.commit()

    audit = AuditService(db)
    await audit.log_safe(
        identity_id=user.id,
        identity_type="user",
        action="generate_api_key",
        resource=f"user:{user_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return {"api_key": raw_key, "message": "API Key 已生成"}


@router.get("/{user_id}/api-key")
async def get_user_api_key(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:read")),
):
    """查看指定用户的 API Key"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not target.api_key_encrypted:
        return {"api_key": None}
    try:
        raw_key = decrypt_api_key(target.api_key_encrypted)
        return {"api_key": raw_key}
    except Exception:
        return {"api_key": None}


@router.delete("/{user_id}/api-key")
async def revoke_user_api_key(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:update")),
):
    """管理员撤销指定用户的 API Key"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not target.api_key_hash:
        raise HTTPException(status_code=400, detail="该用户未配置 API Key")

    target.api_key_hash = None
    target.api_key_encrypted = None
    await db.commit()

    audit = AuditService(db)
    await audit.log_safe(
        identity_id=user.id,
        identity_type="user",
        action="revoke_api_key",
        resource=f"user:{user_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return {"message": "API Key 已撤销"}
