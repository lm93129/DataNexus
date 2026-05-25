"""MCP 鉴权模块单元测试

注意：app.core.security 依赖 python-jose，app.models.user 依赖 sqlalchemy，
在测试环境中可能未安装或导入挂起。
通过 sys.modules 在导入前注入 mock 模块，避免依赖问题。

使用 anyio 运行异步测试（pytest-anyio 已安装）。
"""
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

# --- 注入 mock 的 app.core.security 模块 ---
# 避免 python-jose 未安装导致的 ImportError
_mock_security = types.ModuleType("app.core.security")
_mock_security.verify_token = MagicMock(return_value=None)
_mock_security.verify_api_key = MagicMock(return_value=False)
_mock_security.hash_password = MagicMock(return_value="hashed")
_mock_security.verify_password = MagicMock(return_value=False)
_mock_security.hash_api_key = MagicMock(return_value="hashed")
sys.modules.setdefault("app.core.security", _mock_security)

# --- 注入 mock 的 app.models.user 模块 ---
# 避免 sqlalchemy 导入挂起
_MockUser = MagicMock()
_MockUser.__name__ = "User"
_mock_user_module = types.ModuleType("app.models.user")
_mock_user_module.User = _MockUser
sys.modules.setdefault("app.models.user", _mock_user_module)

# --- 注入 mock 的 sqlalchemy.select ---
# 避免 sqlalchemy 导入挂起（API Key 路径使用）
_mock_sqlalchemy = types.ModuleType("sqlalchemy")
_mock_sqlalchemy.select = MagicMock()
sys.modules.setdefault("sqlalchemy", _mock_sqlalchemy)

from app.mcp.auth import authenticate_mcp_request  # noqa: E402


@pytest.mark.anyio
async def test_rejects_no_credentials():
    """无任何凭证时应返回 401"""
    request = MagicMock()
    request.headers = {}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_rejects_invalid_bearer_token():
    """Bearer Token 无效时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer invalid-token", "X-API-Key": ""}
    db = AsyncMock()

    _mock_security.verify_token = MagicMock(return_value=None)
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_accepts_valid_bearer_token():
    """有效 Bearer Token 且用户活跃时应返回用户对象"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    mock_user = MagicMock()
    mock_user.is_active = True

    _mock_security.verify_token = MagicMock(return_value={"sub": "user:1"})
    db.get = AsyncMock(return_value=mock_user)
    result = await authenticate_mcp_request(request, db)
    assert result == mock_user


@pytest.mark.anyio
async def test_rejects_inactive_user():
    """Token 有效但用户已禁用时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    mock_user = MagicMock()
    mock_user.is_active = False

    _mock_security.verify_token = MagicMock(return_value={"sub": "user:1"})
    db.get = AsyncMock(return_value=mock_user)
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_rejects_token_with_invalid_sub_format():
    """Token sub 字段格式不正确时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    _mock_security.verify_token = MagicMock(return_value={"sub": "invalid-format"})
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_rejects_token_with_non_integer_user_id():
    """Token sub 中 user_id 非整数时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    _mock_security.verify_token = MagicMock(return_value={"sub": "user:abc"})
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_rejects_nonexistent_user():
    """Token 有效但用户不存在时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    _mock_security.verify_token = MagicMock(return_value={"sub": "user:999"})
    db.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_rejects_disabled_api_key_user():
    """API Key 匹配但用户已禁用时应返回 403"""
    request = MagicMock()
    request.headers = {"Authorization": "", "X-API-Key": "valid-api-key"}
    db = AsyncMock()

    mock_user = MagicMock()
    mock_user.is_active = False
    mock_user.api_key_hash = "some-hash"

    # 模拟数据库查询返回一个用户
    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_user]
    db.execute = AsyncMock(return_value=mock_result)

    _mock_security.verify_api_key = MagicMock(return_value=True)
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 403
