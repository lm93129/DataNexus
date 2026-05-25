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
    校验 X-API-Key 请求头，遍历数据库中所有有 api_key_hash 的用户进行比对。
    匹配成功后返回对应 User 对象；若账户已禁用返回 403，Key 无效返回 401。
    """
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供API Key")
    from app.core.security import verify_api_key
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.api_key_hash.isnot(None)))
    for user in result.scalars():
        if verify_api_key(api_key, user.api_key_hash):
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")
            return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key无效")
