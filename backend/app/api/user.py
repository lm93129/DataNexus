from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, decrypt_api_key, encrypt_api_key, hash_api_key, hash_password, verify_password
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.audit import AuditService
from pydantic import BaseModel

import secrets


class LoginRequest(BaseModel):
    username: str
    password: str


class UserProfile(BaseModel):
    id: int
    name: str
    identity_type: str
    role: str
    is_active: bool
    has_api_key: bool

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.name == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash or ""):
        audit = AuditService(db)
        await audit.log(
            identity_id=None,
            identity_type="user",
            action="login_failed",
            resource=f"username:{body.username}",
            ip=request.client.host if request.client else None,
            status="error",
        )
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        audit = AuditService(db)
        await audit.log(
            identity_id=user.id,
            identity_type="user",
            action="login_disabled_account",
            resource=f"user:{user.id}",
            ip=request.client.host if request.client else None,
            status="error",
        )
        raise HTTPException(status_code=403, detail="账户已禁用")

    token = create_access_token(data={"sub": f"user:{user.id}", "type": user.identity_type})
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="login_success",
        resource=f"user:{user.id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserProfile)
async def get_me(user: User = Depends(get_current_user)):
    return UserProfile(
        id=user.id,
        name=user.name,
        identity_type=user.identity_type,
        role=user.role,
        is_active=user.is_active,
        has_api_key=bool(user.api_key_hash),
    )


@router.get("/api-key/current")
async def get_my_api_key(
    user: User = Depends(get_current_user),
):
    """查看当前 API Key"""
    if not user.api_key_encrypted:
        return {"api_key": None}
    try:
        raw_key = decrypt_api_key(user.api_key_encrypted)
        return {"api_key": raw_key}
    except Exception:
        return {"api_key": None}


@router.post("/api-key/generate")
@limiter.limit("5/minute")
async def generate_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成新的 API Key（旧 Key 立即失效）"""
    raw_key = f"dnx_{secrets.token_urlsafe(32)}"
    user.api_key_hash = hash_api_key(raw_key)
    user.api_key_encrypted = encrypt_api_key(raw_key)
    await db.commit()
    await db.refresh(user)

    audit = AuditService(db)
    await audit.log_safe(
        identity_id=user.id,
        identity_type="user",
        action="generate_api_key",
        resource=f"user:{user.id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return {"api_key": raw_key, "message": "API Key 已生成"}


@router.delete("/api-key")
async def revoke_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """撤销当前 API Key"""
    if not user.api_key_hash:
        raise HTTPException(status_code=400, detail="当前未配置 API Key")
    user.api_key_hash = None
    user.api_key_encrypted = None
    await db.commit()
    await db.refresh(user)

    audit = AuditService(db)
    await audit.log_safe(
        identity_id=user.id,
        identity_type="user",
        action="revoke_api_key",
        resource=f"user:{user.id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return {"message": "API Key 已撤销"}
