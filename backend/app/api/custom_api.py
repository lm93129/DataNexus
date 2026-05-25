from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.custom_api import CustomApiCreate, CustomApiResponse, CustomApiUpdate
from app.services.audit import AuditService
from app.services.custom_api import CustomApiService

router = APIRouter(prefix="/custom-apis", tags=["自定义API"])


@router.get("", response_model=list[CustomApiResponse])
@limiter.limit("60/minute")
async def list_custom_apis(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("custom_api:read")),
):
    service = CustomApiService(db)
    return await service.list_all()


@router.get("/{api_id}", response_model=CustomApiResponse)
@limiter.limit("60/minute")
async def get_custom_api(
    request: Request,
    api_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("custom_api:read")),
):
    service = CustomApiService(db)
    api = await service.get_by_id(api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API 不存在")
    return api


@router.post("", response_model=CustomApiResponse, status_code=201)
@limiter.limit("10/minute")
async def create_custom_api(
    request: Request,
    data: CustomApiCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("custom_api:create")),
):
    service = CustomApiService(db)
    try:
        api = await service.create(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="custom_api_create",
        resource=f"custom_api:{api.id}",
        ip=request.client.host if request.client else None,
        status="success",
        request_summary=f"name={api.name}, mode={api.mode}",
    )
    return api


@router.put("/{api_id}", response_model=CustomApiResponse)
@limiter.limit("10/minute")
async def update_custom_api(
    request: Request,
    api_id: int,
    data: CustomApiUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("custom_api:update")),
):
    service = CustomApiService(db)
    try:
        api = await service.update(api_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not api:
        raise HTTPException(status_code=404, detail="API 不存在")
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="custom_api_update",
        resource=f"custom_api:{api_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return api


@router.delete("/{api_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_custom_api(
    request: Request,
    api_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("custom_api:delete")),
):
    service = CustomApiService(db)
    deleted = await service.delete(api_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API 不存在")
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="custom_api_delete",
        resource=f"custom_api:{api_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )


@router.post("/{api_id}/test")
@limiter.limit("5/minute")
async def test_custom_api(
    request: Request,
    api_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("custom_api:read")),
):
    service = CustomApiService(db)
    try:
        result = await service.test_call(api_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
