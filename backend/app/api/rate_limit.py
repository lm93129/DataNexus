from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.schemas.rate_limit import RateLimitCreate, RateLimitResponse, RateLimitUpdate
from app.services.rate_limit import RateLimitService

router = APIRouter(prefix="/rate-limits", tags=["限流管理"])


@router.get("", response_model=list[RateLimitResponse])
async def list_rate_limits(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:read")),
):
    service = RateLimitService(db)
    return await service.list_rules()


@router.post("", response_model=RateLimitResponse, status_code=201)
async def create_rate_limit(
    data: RateLimitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:create")),
):
    service = RateLimitService(db)
    return await service.create_rule(data.model_dump())


@router.put("/{rule_id}", response_model=RateLimitResponse)
async def update_rate_limit(
    rule_id: int,
    data: RateLimitUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:update")),
):
    service = RateLimitService(db)
    rule = await service.update_rule(rule_id, data.model_dump(exclude_unset=True))
    if not rule:
        raise HTTPException(status_code=404, detail="限流规则不存在")
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rate_limit(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("datasource:delete")),
):
    service = RateLimitService(db)
    deleted = await service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="限流规则不存在")
