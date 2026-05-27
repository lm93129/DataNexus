import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

logger = logging.getLogger(__name__)
from app.core.permissions import require_permission
from app.datasource.pool_manager import async_connect, pool_manager
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.datasource import DatasourceCreate, DatasourceResponse, DatasourceUpdate
from app.services.alert import AlertService
from app.services.audit import AuditService
from app.services.datasource import DatasourceService

router = APIRouter(prefix="/datasources", tags=["数据源管理"])


@router.get("", response_model=list[DatasourceResponse])
async def list_datasources(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:read")),
):
    service = DatasourceService(db)
    return await service.list_all()


@router.post("", response_model=DatasourceResponse, status_code=201)
@limiter.limit("10/minute")
async def create_datasource(
    request: Request,
    data: DatasourceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:create")),
):
    service = DatasourceService(db)
    ds = await service.create(data.model_dump())
    # 记录数据源创建审计日志
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="datasource_create",
        resource=f"datasource:{ds.id}",
        request_summary=f"name={data.name}, type={data.type}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return ds


@router.get("/{ds_id}", response_model=DatasourceResponse)
async def get_datasource(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:read")),
):
    service = DatasourceService(db)
    ds = await service.get_by_id(ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ds


@router.put("/{ds_id}", response_model=DatasourceResponse)
@limiter.limit("10/minute")
async def update_datasource(
    request: Request,
    ds_id: int,
    data: DatasourceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:update")),
):
    service = DatasourceService(db)
    ds = await service.update(ds_id, data.model_dump(exclude_unset=True))
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    # 记录数据源更新审计日志
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="datasource_update",
        resource=f"datasource:{ds_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return ds


@router.delete("/{ds_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_datasource(
    request: Request,
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:delete")),
):
    service = DatasourceService(db)
    deleted = await service.delete(ds_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="数据源不存在")
    # 记录数据源删除审计日志
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="datasource_delete",
        resource=f"datasource:{ds_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )


@router.post("/{ds_id}/test")
async def test_datasource_connection(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:read")),
):
    service = DatasourceService(db)
    ds = await service.get_by_id(ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    try:
        password = service.get_password(ds)
        engine = await pool_manager.get_engine(ds, password)
        async with async_connect(engine) as conn:
            ping_sql = "SELECT 1 FROM DUAL" if ds.type == "oracle" else "SELECT 1"
            await conn.execute(text(ping_sql))
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        # 连接失败时触发告警检测
        try:
            alert_service = AlertService(db)
            await alert_service.check_and_trigger(
                action="datasource_test",
                status="error",
                user_id=user.id,
                datasource_id=ds_id,
            )
        except Exception:
            logger.exception("连接测试失败时告警检测异常")
        return {"success": False, "message": f"连接失败: {str(e)}"}
