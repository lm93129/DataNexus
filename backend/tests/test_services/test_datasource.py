import pytest
from unittest.mock import AsyncMock, patch
from app.services.datasource import DatasourceService


@pytest.mark.asyncio
async def test_create_datasource():
    mock_db = AsyncMock()
    service = DatasourceService(mock_db)
    data = {
        "name": "test_mysql",
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "reader",
        "password": "secret123",
    }
    result = await service.create(data)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_list_datasources():
    from unittest.mock import MagicMock
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    service = DatasourceService(mock_db)
    result = await service.list_all()
    mock_db.execute.assert_called_once()
    assert result == []


def test_encrypt_decrypt():
    mock_db = AsyncMock()
    service = DatasourceService(mock_db)
    original = "my_secret_password"
    encrypted = service._encrypt(original)
    decrypted = service._decrypt(encrypted)
    assert decrypted == original
    assert encrypted != original


from app.datasource.pool_manager import PoolManager


def test_check_driver_postgresql():
    pm = PoolManager()
    # asyncpg 已安装，不应抛异常
    pm._check_driver("postgresql")


def test_check_driver_unknown_raises():
    pm = PoolManager()
    with pytest.raises(RuntimeError, match="需要安装驱动"):
        pm._check_driver("oracle")


def test_build_url_escapes_special_chars():
    from unittest.mock import MagicMock, patch
    pm = PoolManager()
    ds = MagicMock()
    ds.type = "postgresql"
    ds.username = "user@name"
    ds.host = "localhost"
    ds.port = 5432
    ds.database = "testdb"

    with patch.object(pm, "_check_driver"):
        url = pm._build_url(ds, "p@ss:word/123")
    assert "user%40name" in url
    assert "p%40ss%3Aword%2F123" in url
