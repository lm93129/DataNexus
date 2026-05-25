from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.metadata import MetadataService

router = APIRouter(prefix="/metadata", tags=["元数据"])


@router.get("/tables/{datasource_id}")
@limiter.limit("60/minute")
async def get_tables(
    request: Request,
    datasource_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("metadata:read")),
):
    service = MetadataService(db)
    tables = await service.get_tables(datasource_id)
    return [{"id": t.id, "table_name": t.table_name, "table_comment": t.table_comment} for t in tables]


@router.get("/columns/{table_metadata_id}")
@limiter.limit("60/minute")
async def get_columns(
    request: Request,
    table_metadata_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("metadata:read")),
):
    service = MetadataService(db)
    columns = await service.get_columns(table_metadata_id)
    return [
        {
            "column_name": c.column_name,
            "data_type": c.data_type,
            "column_comment": c.column_comment,
            "is_primary_key": c.is_primary_key,
        }
        for c in columns
    ]
