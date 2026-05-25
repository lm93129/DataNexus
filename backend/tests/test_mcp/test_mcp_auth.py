"""MCP 鉴权模块单元测试

使用 unittest.mock.patch 对 app.core.security 中的函数进行 mock，
确保无论测试执行顺序如何都能正确隔离。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.mcp.auth import authenticate_mcp_request


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
@patch("app.core.security.verify_token", return_value=None)
async def test_rejects_invalid_bearer_token(mock_verify):
    """Bearer Token 无效时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer invalid-token", "X-API-Key": ""}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
@patch("app.core.security.verify_token", return_value={"sub": "user:1"})
async def test_accepts_valid_bearer_token(mock_verify):
    """有效 Bearer Token 且用户活跃时应返回用户对象"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    mock_user = MagicMock()
    mock_user.is_active = True
    db.get = AsyncMock(return_value=mock_user)

    result = await authenticate_mcp_request(request, db)
    assert result == mock_user


@pytest.mark.anyio
@patch("app.core.security.verify_token", return_value={"sub": "user:1"})
async def test_rejects_inactive_user(mock_verify):
    """Token 有效但用户已禁用时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    mock_user = MagicMock()
    mock_user.is_active = False
    db.get = AsyncMock(return_value=mock_user)

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
@patch("app.core.security.verify_token", return_value={"sub": "invalid-format"})
async def test_rejects_token_with_invalid_sub_format(mock_verify):
    """Token sub 字段格式不正确时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
@patch("app.core.security.verify_token", return_value={"sub": "user:abc"})
async def test_rejects_token_with_non_integer_user_id(mock_verify):
    """Token sub 中 user_id 非整数时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
@patch("app.core.security.verify_token", return_value={"sub": "user:999"})
async def test_rejects_nonexistent_user(mock_verify):
    """Token 有效但用户不存在时应返回 401"""
    request = MagicMock()
    request.headers = {"Authorization": "Bearer valid-token", "X-API-Key": ""}
    db = AsyncMock()

    db.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
@patch("app.core.security.verify_api_key", return_value=True)
async def test_rejects_disabled_api_key_user(mock_verify_key):
    """API Key 匹配但用户已禁用时应返回 403"""
    request = MagicMock()
    request.headers = {"Authorization": "", "X-API-Key": "valid-api-key"}
    db = AsyncMock()

    mock_user = MagicMock()
    mock_user.is_active = False
    mock_user.api_key_hash = "some-hash"

    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_user]
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_mcp_request(request, db)
    assert exc_info.value.status_code == 403
