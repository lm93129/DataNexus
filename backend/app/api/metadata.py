from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.datasource.pool_manager import pool_manager
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.audit import AuditService
from app.services.datasource import DatasourceService
from app.services.metadata import MetadataService

router = APIRouter(prefix="/metadata", tags=["元数据"])


class UpdateCommentRequest(BaseModel):
    comment: str = ""


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
    # 审计日志
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="metadata_read_tables",
        resource=f"datasource:{datasource_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
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
    # 审计日志
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="metadata_read_columns",
        resource=f"table_metadata:{table_metadata_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return [
        {
            "id": c.id,
            "column_name": c.column_name,
            "data_type": c.data_type,
            "column_comment": c.column_comment,
            "is_primary_key": c.is_primary_key,
            "desensitize_rule": c.desensitize_rule,
        }
        for c in columns
    ]


@router.post("/sync/{datasource_id}")
@limiter.limit("5/minute")
async def sync_metadata(
    request: Request,
    datasource_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("metadata:read")),
):
    ds_service = DatasourceService(db)
    ds = await ds_service.get_by_id(datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    try:
        password = ds_service.get_password(ds)
        engine = await pool_manager.get_engine(ds, password)
        meta_service = MetadataService(db)
        await meta_service.sync_from_source(datasource_id, engine, ds_type=ds.type)
        tables = await meta_service.get_tables(datasource_id)

        audit = AuditService(db)
        await audit.log(
            identity_id=user.id,
            identity_type="user",
            action="metadata_sync",
            resource=f"datasource:{datasource_id}",
            ip=request.client.host if request.client else None,
            status="success",
        )
        return {"success": True, "table_count": len(tables)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/search")
@limiter.limit("60/minute")
async def search_metadata(
    request: Request,
    keyword: str = Query(..., min_length=1, max_length=100),
    datasource_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("metadata:read")),
):
    """搜索表名/列名/备注"""
    service = MetadataService(db)
    result = await service.search(keyword, datasource_id)
    # 审计日志
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="metadata_search",
        resource=f"keyword:{keyword}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return {
        "tables": [
            {"id": t.id, "datasource_id": t.datasource_id, "table_name": t.table_name, "table_comment": t.table_comment}
            for t in result["tables"]
        ],
        "columns": [
            {"id": c.id, "table_metadata_id": c.table_metadata_id, "column_name": c.column_name, "data_type": c.data_type, "column_comment": c.column_comment}
            for c in result["columns"]
        ],
    }


@router.put("/tables/{table_id}/comment")
@limiter.limit("30/minute")
async def update_table_comment(
    request: Request,
    table_id: int,
    body: UpdateCommentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("metadata:write")),
):
    """更新表的业务注释"""
    service = MetadataService(db)
    table = await service.update_table_comment(table_id, body.comment)
    if not table:
        raise HTTPException(status_code=404, detail="表不存在")
    return {"id": table.id, "table_name": table.table_name, "table_comment": table.table_comment}


@router.put("/columns/{column_id}/comment")
@limiter.limit("30/minute")
async def update_column_comment(
    request: Request,
    column_id: int,
    body: UpdateCommentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("metadata:write")),
):
    """更新字段的业务注释"""
    service = MetadataService(db)
    column = await service.update_column_comment(column_id, body.comment)
    if not column:
        raise HTTPException(status_code=404, detail="字段不存在")
    return {"id": column.id, "column_name": column.column_name, "column_comment": column.column_comment}
