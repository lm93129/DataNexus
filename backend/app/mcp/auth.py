"""MCP 请求身份鉴权模块

所有重量级依赖（sqlalchemy、jose 等）均采用延迟导入，
确保模块本身可在缺少部分依赖的测试环境中正常加载。
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status


async def authenticate_mcp_request(request: Request, db):
    """从 MCP SSE 请求中提取并验证身份

    支持两种认证方式：
    1. Bearer Token（JWT）：从 Authorization 头提取
    2. API Key：从 X-API-Key 头提取，遍历用户表匹配哈希

    参数：
        request: FastAPI/Starlette Request 对象
        db: AsyncSession 数据库会话

    返回已验证的 User 对象。
    """
    # 延迟导入，避免在测试环境中因缺少依赖而导致模块加载失败
    from app.core.security import verify_api_key, verify_token
    from app.models.user import User

    auth_header = request.headers.get("Authorization", "")
    api_key = request.headers.get("X-API-Key", "")

    # --- Bearer Token 认证 ---
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token无效",
            )
        sub = payload.get("sub", "")
        if not sub.startswith("user:"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token格式无效",
            )
        try:
            user_id = int(sub.split(":")[1])
        except (IndexError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token格式无效",
            )
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已禁用",
            )
        return user

    # --- API Key 认证 ---
    if api_key:
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.api_key_hash.isnot(None)))
        for user in result.scalars():
            if verify_api_key(api_key, user.api_key_hash):
                if not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="账户已禁用",
                    )
                return user

    # --- 无有效凭证 ---
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未提供有效认证",
    )
