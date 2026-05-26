"""
认证依赖模块

提供 FastAPI 路由使用的认证依赖：
- get_current_user: 校验 Bearer JWT，从数据库加载完整 User 对象
- get_api_key_identity: 校验 X-API-Key 请求头，返回对应 User 对象
"""
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    校验 Bearer JWT 并从数据库加载完整 User 对象。

    Token 的 sub 字段格式为 "user:<id>"，例如 "user:42"。
    若用户不存在或已被禁用，返回 401。
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证信息")
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token无效或已过期")

    sub = payload.get("sub", "")
    if not sub.startswith("user:"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token格式无效")
    try:
        user_id = int(sub.split(":")[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token格式无效")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


async def get_api_key_identity(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    校验 X-API-Key 请求头。
    使用前缀索引（前 8 字符）快速定位候选用户，再对单条做 PBKDF2 验证。
    """
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供API Key")
    from app.core.security import verify_api_key
    from sqlalchemy import select

    prefix = api_key[:8]
    # 前缀索引快速查找
    result = await db.execute(
        select(User).where(User.api_key_prefix == prefix, User.api_key_hash.isnot(None)).limit(5)
    )
    for user in result.scalars():
        if verify_api_key(api_key, user.api_key_hash):
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")
            return user

    # Fallback：兼容 api_key_prefix 尚未回填的用户（迁移过渡期）
    result = await db.execute(
        select(User).where(User.api_key_prefix.is_(None), User.api_key_hash.isnot(None))
    )
    for user in result.scalars():
        if verify_api_key(api_key, user.api_key_hash):
            # 回填前缀，后续请求走快速路径
            user.api_key_prefix = api_key[:8]
            await db.commit()
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key无效")
