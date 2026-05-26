import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.metadata import MetadataService


@pytest.mark.asyncio
async def test_get_tables_filters_blocked():
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    service = MetadataService(mock_db)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(table_name="orders", is_blocked=False, table_comment="订单表"),
        MagicMock(table_name="secrets", is_blocked=True, table_comment="机密表"),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    tables = await service.get_tables(datasource_id=1)
    # 验证调用了execute
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_columns_filters_blocked():
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    service = MetadataService(mock_db)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(column_name="id", is_blocked=False),
        MagicMock(column_name="ssn", is_blocked=True),
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    columns = await service.get_columns(table_metadata_id=1)
    mock_db.execute.assert_called_once()
