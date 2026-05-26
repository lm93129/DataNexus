import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.models.alert import NotificationChannel

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务：将告警推送到企业微信/钉钉/飞书 Webhook"""

    async def send_alert(self, record: AlertRecord, channels: list[NotificationChannel]):
        """向多个渠道发送告警通知（异步，不阻塞）"""
        # 提取纯数据，避免 ORM 对象在 task 中因 session 关闭而失效
        record_data = {
            "rule_name": record.rule_name,
            "rule_type": record.rule_type,
            "detail": record.detail,
            "triggered_at": record.triggered_at,
        }
        for channel in channels:
            if not channel.is_active:
                continue
            ch_data = {
                "name": channel.name,
                "channel_type": channel.channel_type,
                "webhook_url": channel.webhook_url,
            }
            asyncio.create_task(self._dispatch(ch_data, record_data))

    async def test_channel(self, channel: NotificationChannel) -> tuple[bool, str]:
        """测试渠道连通性，返回 (成功, 消息)"""
        payload = self._build_test_payload(channel.channel_type)
        return await self._send_webhook(channel.webhook_url, payload)

    async def _dispatch(self, channel: dict, record: dict):
        """分发到对应渠道"""
        try:
            if channel["channel_type"] == "wecom":
                payload = self._build_wecom_payload(record)
            elif channel["channel_type"] == "dingtalk":
                payload = self._build_dingtalk_payload(record)
            elif channel["channel_type"] == "feishu":
                payload = self._build_feishu_payload(record)
            else:
                logger.warning("未知渠道类型: %s", channel["channel_type"])
                return
            success, msg = await self._send_webhook(channel["webhook_url"], payload)
            if not success:
                logger.warning("通知发送失败 [%s/%s]: %s", channel["name"], channel["channel_type"], msg)
        except Exception:
            logger.exception("通知发送异常 [%s]", channel["name"])

    # ========== 消息体构建 ==========

    def _build_wecom_payload(self, record: dict) -> dict:
        """企业微信 Webhook 消息体"""
        content = (
            f"**🚨 DataNexus 告警通知**\n"
            f"> 规则：{record['rule_name']}\n"
            f"> 类型：{record['rule_type']}\n"
            f"> 详情：{record['detail']}\n"
            f"> 时间：{self._format_time(record['triggered_at'])}"
        )
        return {"msgtype": "markdown", "markdown": {"content": content}}

    def _build_dingtalk_payload(self, record: dict) -> dict:
        """钉钉 Webhook 消息体"""
        text = (
            f"**DataNexus 告警通知**\n\n"
            f"- 规则：{record['rule_name']}\n"
            f"- 类型：{record['rule_type']}\n"
            f"- 详情：{record['detail']}\n"
            f"- 时间：{self._format_time(record['triggered_at'])}"
        )
        return {
            "msgtype": "markdown",
            "markdown": {"title": f"告警: {record['rule_name']}", "text": text},
        }

    def _build_feishu_payload(self, record: dict) -> dict:
        """飞书 Webhook 卡片消息体"""
        content = (
            f"**规则**：{record['rule_name']}\n"
            f"**类型**：{record['rule_type']}\n"
            f"**详情**：{record['detail']}\n"
            f"**时间**：{self._format_time(record['triggered_at'])}"
        )
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "DataNexus 告警通知"},
                    "template": "red",
                },
                "elements": [{"tag": "markdown", "content": content}],
            },
        }

    def _build_test_payload(self, channel_type: str) -> dict:
        """构建测试消息"""
        if channel_type == "wecom":
            return {
                "msgtype": "markdown",
                "markdown": {"content": "**DataNexus 通知渠道测试**\n> 连接成功，此渠道配置正常。"},
            }
        elif channel_type == "dingtalk":
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": "DataNexus 测试",
                    "text": "**DataNexus 通知渠道测试**\n\n连接成功，此渠道配置正常。",
                },
            }
        else:
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": "DataNexus 通知渠道测试"},
                        "template": "green",
                    },
                    "elements": [{"tag": "markdown", "content": "连接成功，此渠道配置正常。"}],
                },
            }

    # ========== 工具方法 ==========

    async def _send_webhook(self, url: str, payload: dict) -> tuple[bool, str]:
        """发送 Webhook 请求"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return True, "发送成功"
                return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except httpx.TimeoutException:
            return False, "请求超时"
        except Exception as e:
            return False, f"请求异常: {str(e)[:200]}"

    def _format_time(self, dt: datetime | None) -> str:
        if not dt:
            return "未知"
        local_dt = dt.astimezone(timezone(timedelta(hours=8)))
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")