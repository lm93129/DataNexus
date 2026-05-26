import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.services.alert import AlertService

router = APIRouter(prefix="/alerts", tags=["告警管理"])


class AlertRuleCreate(BaseModel):
    name: str
    rule_type: str
    threshold_config: dict = Field(default_factory=dict)
    scope: str = "global"
    target_id: int | None = None
    suppress_minutes: int = 10


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    rule_type: str | None = None
    threshold_config: dict | None = None
    scope: str | None = None
    target_id: int | None = None
    is_active: bool | None = None
    suppress_minutes: int | None = None


@router.get("/rules")
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    rules = await service.list_rules()
    return [_rule_to_dict(r) for r in rules]


@router.post("/rules")
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    data = body.model_dump()
    data["threshold_config"] = json.dumps(data["threshold_config"])
    rule = await service.create_rule(data)
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "threshold_config" in data:
        data["threshold_config"] = json.dumps(data["threshold_config"])
    rule = await service.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    if not await service.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="规则不存在")


@router.get("/records")
async def list_alert_records(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    records = await service.list_records(status=status, limit=limit)
    return [_record_to_dict(r) for r in records]


@router.get("/records/pending-count")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    count = await service.pending_count()
    return {"count": count}


@router.put("/records/{record_id}/acknowledge")
async def acknowledge_alert(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    if not await service.acknowledge_record(record_id):
        raise HTTPException(status_code=404, detail="记录不存在或已处理")
    return {"ok": True}


@router.put("/records/{record_id}/resolve")
async def resolve_alert(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    service = AlertService(db)
    if not await service.resolve_record(record_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


def _rule_to_dict(r: "AlertRule") -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "rule_type": r.rule_type,
        "threshold_config": json.loads(r.threshold_config) if r.threshold_config else {},
        "scope": r.scope,
        "target_id": r.target_id,
        "is_active": r.is_active,
        "suppress_minutes": r.suppress_minutes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _record_to_dict(r: "AlertRecord") -> dict:
    return {
        "id": r.id,
        "rule_id": r.rule_id,
        "rule_name": r.rule_name,
        "rule_type": r.rule_type,
        "detail": r.detail,
        "status": r.status,
        "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
        "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
    }
