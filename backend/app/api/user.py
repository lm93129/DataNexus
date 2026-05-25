from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.audit import AuditService
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.name == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash or ""):
        # 记录登录失败审计日志
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
        raise HTTPException(status_code=403, detail="账户已禁用")

    token = create_access_token(data={"sub": f"user:{user.id}", "type": user.identity_type})
    # 记录登录成功审计日志
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


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return user
