import pytest
from unittest.mock import AsyncMock
from app.services.query import QueryService


@pytest.mark.asyncio
async def test_query_rejects_dangerous_sql():
    mock_db = AsyncMock()
    service = QueryService(mock_db)
    result = await service.execute_query(datasource_id=1, sql="DROP TABLE users", identity_id=1)
    assert result["success"] is False
    assert "仅允许SELECT" in result["error"]


@pytest.mark.asyncio
async def test_query_rejects_delete():
    mock_db = AsyncMock()
    service = QueryService(mock_db)
    result = await service.execute_query(datasource_id=1, sql="DELETE FROM users", identity_id=1)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_query_rejects_pg_sleep():
    mock_db = AsyncMock()
    service = QueryService(mock_db)
    result = await service.execute_query(datasource_id=1, sql="SELECT pg_sleep(10)", identity_id=1)
    assert result["success"] is False
    assert "危险函数" in result["error"]
