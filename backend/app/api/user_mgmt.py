from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse, UserUpdate
from app.services.audit import AuditService

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("user:read")),
):
    result = await db.execute(select(User).where(User.identity_type == "user"))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            username=u.name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


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
    return UserResponse(
        id=new_user.id,
        username=new_user.name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat() if new_user.created_at else None,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
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
    await db.commit()
    await db.refresh(target)
    return UserResponse(
        id=target.id,
        username=target.name,
        role=target.role,
        is_active=target.is_active,
        created_at=target.created_at.isoformat() if target.created_at else None,
    )


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
