import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_api import CustomApi

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_ssrf_target(url: str) -> bool:
    """检查 URL 是否指向内网/本地地址"""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return True
    # 阻止常见内网主机名
    if hostname in ("localhost", "metadata.google.internal", "169.254.169.254"):
        return True
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, addr in resolved:
            ip = ipaddress.ip_address(addr[0])
            for net in BLOCKED_NETWORKS:
                if ip in net:
                    return True
    except (socket.gaierror, ValueError):
        return True
    return False


class CustomApiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[CustomApi]:
        result = await self.db.execute(select(CustomApi).order_by(CustomApi.id))
        return list(result.scalars().all())

    async def get_by_id(self, api_id: int) -> CustomApi | None:
        result = await self.db.execute(
            select(CustomApi).where(CustomApi.id == api_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> CustomApi:
        self._validate_config(data.get("config_json", ""))
        api = CustomApi(**data)
        self.db.add(api)
        await self.db.commit()
        await self.db.refresh(api)
        return api

    async def update(self, api_id: int, data: dict) -> CustomApi | None:
        api = await self.get_by_id(api_id)
        if not api:
            return None
        if "config_json" in data and data["config_json"] is not None:
            self._validate_config(data["config_json"])
        for key, value in data.items():
            if value is not None:
                setattr(api, key, value)
        api.version += 1
        await self.db.commit()
        await self.db.refresh(api)
        return api

    async def delete(self, api_id: int) -> bool:
        api = await self.get_by_id(api_id)
        if not api:
            return False
        await self.db.delete(api)
        await self.db.commit()
        return True

    async def test_call(self, api_id: int) -> dict:
        """测试调用自定义 API"""
        api = await self.get_by_id(api_id)
        if not api:
            raise ValueError("API 不存在")
        config = json.loads(api.config_json)
        url = config.get("url", "")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})

        if _is_ssrf_target(url):
            return {"success": False, "message": "安全限制：不允许访问内网地址"}

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                resp = await client.request(method, url, headers=headers)
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "message": f"{method} {url} → {resp.status_code}",
                    "body_preview": resp.text[:500],
                }
        except Exception as e:
            return {"success": False, "message": f"请求失败: {str(e)}"}

    def _validate_config(self, config_json: str) -> None:
        """验证 config_json 格式"""
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            raise ValueError("config_json 不是有效的 JSON")
        if "url" not in config:
            raise ValueError("config_json 必须包含 'url' 字段")
        if "method" not in config:
            raise ValueError("config_json 必须包含 'method' 字段")
        if _is_ssrf_target(config["url"]):
            raise ValueError("安全限制：URL 不允许指向内网地址")
