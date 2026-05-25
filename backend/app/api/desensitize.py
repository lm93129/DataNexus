from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.desensitize import (
    ColumnRuleAssign,
    DesensitizeRuleCreate,
    DesensitizeRuleResponse,
    DesensitizeRuleUpdate,
)
from app.services.audit import AuditService
from app.services.desensitize import DesensitizeRuleService

router = APIRouter(prefix="/desensitize-rules", tags=["脱敏规则"])


@router.get("", response_model=list[DesensitizeRuleResponse])
@limiter.limit("60/minute")
async def list_rules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("desensitize:read")),
):
    service = DesensitizeRuleService(db)
    return await service.list_all()


@router.post("", response_model=DesensitizeRuleResponse, status_code=201)
@limiter.limit("10/minute")
async def create_rule(
    request: Request,
    data: DesensitizeRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("desensitize:create")),
):
    service = DesensitizeRuleService(db)
    rule = await service.create(data.model_dump())
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="desensitize_rule_create",
        resource=f"rule:{rule.id}",
        ip=request.client.host if request.client else None,
        status="success",
        request_summary=f"name={rule.name}",
    )
    return rule


@router.put("/{rule_id}", response_model=DesensitizeRuleResponse)
@limiter.limit("10/minute")
async def update_rule(
    request: Request,
    rule_id: int,
    data: DesensitizeRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("desensitize:update")),
):
    service = DesensitizeRuleService(db)
    try:
        rule = await service.update(rule_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="desensitize_rule_update",
        resource=f"rule:{rule_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )
    return rule


@router.delete("/{rule_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("desensitize:delete")),
):
    service = DesensitizeRuleService(db)
    try:
        deleted = await service.delete(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="规则不存在")
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="desensitize_rule_delete",
        resource=f"rule:{rule_id}",
        ip=request.client.host if request.client else None,
        status="success",
    )


@router.put("/columns/{column_id}/rule")
@limiter.limit("30/minute")
async def assign_column_rule(
    request: Request,
    column_id: int,
    data: ColumnRuleAssign,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("desensitize:update")),
):
    service = DesensitizeRuleService(db)
    try:
        col = await service.assign_to_column(column_id, data.rule_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not col:
        raise HTTPException(status_code=404, detail="列不存在")
    audit = AuditService(db)
    await audit.log(
        identity_id=user.id,
        identity_type="user",
        action="desensitize_assign",
        resource=f"column:{column_id}",
        ip=request.client.host if request.client else None,
        status="success",
        request_summary=f"rule={data.rule_name}",
    )
    return {"success": True, "column_id": column_id, "rule_name": data.rule_name}
