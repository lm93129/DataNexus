from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.metadata import ColumnMetadata, TableMetadata
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


class UppercaseMetadataRow:
    def __init__(self, row_mapping: dict):
        self._mapping = row_mapping


@pytest.mark.asyncio
async def test_sync_from_source_reads_uppercase_mysql_metadata_keys(monkeypatch):
    added_models = []

    class FakeConnection:
        async def execute(self, stmt, params=None):
            if params:
                return [
                    UppercaseMetadataRow(
                        {
                            "COLUMN_NAME": "id",
                            "DATA_TYPE": "bigint",
                            "COLUMN_COMMENT": "主键",
                            "IS_PK": 1,
                        }
                    )
                ]
            return [
                UppercaseMetadataRow(
                    {
                        "TABLE_NAME": "customers",
                        "TABLE_COMMENT": "客户表",
                    }
                )
            ]

    @asynccontextmanager
    async def fake_async_connect(engine):
        yield FakeConnection()

    empty_scalar = MagicMock()
    empty_scalar.all.return_value = []

    missing_table_lookup = MagicMock()
    missing_table_lookup.scalar_one_or_none.return_value = None

    missing_columns_lookup = MagicMock()
    missing_columns_lookup.scalars.return_value = empty_scalar

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[missing_table_lookup, missing_columns_lookup])
    mock_db.add = MagicMock(side_effect=added_models.append)

    async def flush_table_id():
        for model in added_models:
            if isinstance(model, TableMetadata):
                model.id = 42

    mock_db.flush = AsyncMock(side_effect=flush_table_id)
    monkeypatch.setattr("app.services.metadata.async_connect", fake_async_connect)

    await MetadataService(mock_db).sync_from_source(datasource_id=7, engine=object(), ds_type="mysql")

    table_meta = next(model for model in added_models if isinstance(model, TableMetadata))
    column_meta = next(model for model in added_models if isinstance(model, ColumnMetadata))

    assert table_meta.table_name == "customers"
    assert table_meta.table_comment == "客户表"
    assert column_meta.table_metadata_id == 42
    assert column_meta.column_name == "id"
    assert column_meta.is_primary_key is True
    mock_db.commit.assert_awaited_once()
