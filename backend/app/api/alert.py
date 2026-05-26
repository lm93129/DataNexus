import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_permission
from app.models.alert import NotificationChannel, alert_rule_channels
from app.models.user import User
from app.services.alert import AlertService
from app.services.notification import NotificationService

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
    user: User = Depends(require_permission("alert:read")),
):
    service = AlertService(db)
    rules = await service.list_rules()
    return [_rule_to_dict(r) for r in rules]


@router.post("/rules")
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
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
    user: User = Depends(require_permission("alert:manage")),
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
    user: User = Depends(require_permission("alert:manage")),
):
    service = AlertService(db)
    if not await service.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="规则不存在")


@router.get("/records")
async def list_alert_records(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:read")),
):
    service = AlertService(db)
    records = await service.list_records(status=status, limit=limit)
    return [_record_to_dict(r) for r in records]


@router.get("/records/pending-count")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:read")),
):
    service = AlertService(db)
    count = await service.pending_count()
    return {"count": count}


@router.put("/records/{record_id}/acknowledge")
async def acknowledge_alert(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
):
    service = AlertService(db)
    if not await service.acknowledge_record(record_id):
        raise HTTPException(status_code=404, detail="记录不存在或已处理")
    return {"ok": True}


@router.put("/records/{record_id}/resolve")
async def resolve_alert(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
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


# ========== 通知渠道 ==========


class ChannelCreate(BaseModel):
    name: str = Field(max_length=100)
    channel_type: str = Field(pattern=r"^(wecom|dingtalk|feishu)$")
    webhook_url: str = Field(max_length=500)


class ChannelUpdate(BaseModel):
    name: str | None = None
    channel_type: str | None = Field(default=None, pattern=r"^(wecom|dingtalk|feishu)$")
    webhook_url: str | None = None
    is_active: bool | None = None


class RuleChannelsUpdate(BaseModel):
    channel_ids: list[int]


@router.get("/channels")
async def list_channels(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:read")),
):
    result = await db.execute(
        select(NotificationChannel).order_by(NotificationChannel.id.desc())
    )
    channels = result.scalars().all()
    return [_channel_to_dict(c) for c in channels]


@router.post("/channels")
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
):
    channel = NotificationChannel(
        name=body.name,
        channel_type=body.channel_type,
        webhook_url=body.webhook_url,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return _channel_to_dict(channel)


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: int,
    body: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
):
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(channel, k, v)
    await db.commit()
    await db.refresh(channel)
    return _channel_to_dict(channel)


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
):
    result = await db.execute(
        delete(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="渠道不存在")
    await db.commit()


@router.post("/channels/{channel_id}/test")
async def test_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
):
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    service = NotificationService()
    success, msg = await service.test_channel(channel)
    return {"success": success, "message": msg}


@router.get("/rules/{rule_id}/channels")
async def get_rule_channels(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:read")),
):
    result = await db.execute(
        select(alert_rule_channels.c.channel_id)
        .where(alert_rule_channels.c.rule_id == rule_id)
    )
    return [row[0] for row in result.all()]


@router.put("/rules/{rule_id}/channels")
async def set_rule_channels(
    rule_id: int,
    body: RuleChannelsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("alert:manage")),
):
    # 先删除旧关联
    await db.execute(
        delete(alert_rule_channels).where(alert_rule_channels.c.rule_id == rule_id)
    )
    # 插入新关联
    for cid in body.channel_ids:
        await db.execute(
            alert_rule_channels.insert().values(rule_id=rule_id, channel_id=cid)
        )
    await db.commit()
    return {"ok": True}


def _channel_to_dict(c: NotificationChannel) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "channel_type": c.channel_type,
        "webhook_url": c.webhook_url,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
