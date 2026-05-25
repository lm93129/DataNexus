import pytest
from unittest.mock import AsyncMock
from app.services.audit import AuditService


@pytest.mark.asyncio
async def test_log_action():
    mock_db = AsyncMock()
    service = AuditService(mock_db)
    await service.log(
        identity_id=1,
        identity_type="model",
        action="query_database",
        resource="datasource:1",
        request_summary="SELECT * FROM orders LIMIT 10",
        response_summary="10 rows returned",
        ip="192.168.1.100",
        duration_ms=45,
        status="success",
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


class TestSanitizeSql:
    def test_replaces_string_literals(self):
        sql = "SELECT * FROM users WHERE name = '张三' AND phone = '13812345678'"
        result = AuditService.sanitize_sql(sql)
        assert "张三" not in result
        assert "13812345678" not in result

    def test_replaces_number_literals(self):
        sql = "SELECT * FROM users WHERE id = 12345"
        result = AuditService.sanitize_sql(sql)
        assert "12345" not in result

    def test_handles_invalid_sql(self):
        sql = "NOT VALID SQL {{{"
        result = AuditService.sanitize_sql(sql)
        assert isinstance(result, str)

    def test_preserves_structure(self):
        sql = "SELECT id, name FROM users WHERE age > 18 LIMIT 10"
        result = AuditService.sanitize_sql(sql)
        assert "SELECT" in result
        assert "users" in result
