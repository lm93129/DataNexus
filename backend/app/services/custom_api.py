import base64
import ipaddress
import json
import re
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


def _extract_json_path(data, path: str):
    """简化的 JSONPath 提取，支持点号分隔和数组索引"""
    parts = re.split(r"\.|\[(\d+)\]", path)
    parts = [p for p in parts if p is not None and p != ""]
    current = data
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (IndexError, ValueError):
                return None
        else:
            return None
    return current


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
        self._validate_config(data.get("config_json", ""), mode=data.get("mode", "custom"))
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
            mode = data.get("mode", api.mode)
            self._validate_config(data["config_json"], mode=mode)
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

    async def test_call(self, api_id: int, test_params: dict | None = None) -> dict:
        """测试调用自定义 API"""
        api = await self.get_by_id(api_id)
        if not api:
            raise ValueError("API 不存在")

        config = json.loads(api.config_json)

        # low_code 模式使用精细执行引擎
        if api.mode == "low_code":
            return await self._execute_low_code(config, test_params or {})

        # custom 模式保持原有逻辑
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

    async def _execute_low_code(self, config: dict, params: dict) -> dict:
        """低代码模式精细执行引擎"""
        url = config.get("url", "")
        method = config.get("method", "GET").upper()
        timeout = config.get("timeout", 30)
        headers = dict(config.get("headers", {}))
        param_defs = config.get("params", [])
        body_template = config.get("body_template")
        response_cfg = config.get("response", {})

        # 1. 认证注入
        auth_cfg = config.get("auth", {"type": "none"})
        auth_type = auth_cfg.get("type", "none")
        auth_config = auth_cfg.get("config", {})

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
        elif auth_type == "basic":
            username = auth_config.get("username", "")
            password = auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif auth_type == "api_key":
            header_name = auth_config.get("header", "X-API-Key")
            headers[header_name] = auth_config.get("value", "")

        # 2. 参数路由
        query_params: dict = {}
        body_data: dict = {}

        for p_def in param_defs:
            p_name = p_def.get("name", "")
            p_in = p_def.get("in", "query")
            p_required = p_def.get("required", False)
            p_default = p_def.get("default")

            # 取值：优先从调用参数中取，否则用默认值
            if p_name in params:
                value = params[p_name]
            elif p_default is not None:
                value = p_default
            elif p_required:
                return {"success": False, "message": f"缺少必填参数: {p_name}"}
            else:
                continue

            if p_in == "path":
                url = url.replace(f"{{{p_name}}}", str(value))
            elif p_in == "query":
                query_params[p_name] = value
            elif p_in == "body":
                body_data[p_name] = value
            elif p_in == "header":
                headers[p_name] = str(value)

        # 3. Body 构建
        request_body = None
        if method != "GET":
            if body_template:
                # 模板替换 {{param_name}}
                tpl = json.dumps(body_template) if isinstance(body_template, dict) else str(body_template)
                for key, val in body_data.items():
                    replacement = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
                    tpl = tpl.replace(f"{{{{{key}}}}}", replacement)
                try:
                    request_body = json.loads(tpl)
                except json.JSONDecodeError:
                    request_body = tpl
            elif body_data:
                request_body = body_data

        # 4. SSRF 检查
        if _is_ssrf_target(url):
            return {"success": False, "message": "安全限制：不允许访问内网地址"}

        # 5. 发送请求
        try:
            async with httpx.AsyncClient(timeout=float(timeout), follow_redirects=False) as client:
                if method == "GET":
                    resp = await client.get(url, params=query_params, headers=headers)
                else:
                    resp = await client.request(
                        method, url,
                        params=query_params,
                        json=request_body,
                        headers=headers,
                    )

                # 6. 响应提取
                try:
                    resp_json = resp.json()
                except Exception:
                    resp_json = None

                extract_path = response_cfg.get("extract") if response_cfg else None
                if extract_path and resp_json is not None:
                    extracted = _extract_json_path(resp_json, extract_path)
                else:
                    extracted = resp_json if resp_json is not None else resp.text[:2000]

                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "message": f"{method} {url} → {resp.status_code}",
                    "data": extracted,
                }
        except Exception as e:
            return {"success": False, "message": f"请求失败: {str(e)}"}

    def _validate_config(self, config_json: str, mode: str = "custom") -> None:
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

        # low_code 模式额外验证
        if mode == "low_code":
            self._validate_low_code_config(config)

    def _validate_low_code_config(self, config: dict) -> None:
        """low_code 模式的结构化配置验证"""
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        method = config.get("method", "").upper()
        if method not in valid_methods:
            raise ValueError(f"method 必须是 {'/'.join(valid_methods)} 之一")

        # 验证 auth
        auth = config.get("auth", {"type": "none"})
        valid_auth_types = {"none", "bearer", "basic", "api_key"}
        if auth.get("type") not in valid_auth_types:
            raise ValueError(f"auth.type 必须是 {'/'.join(valid_auth_types)} 之一")

        # 验证 params
        params = config.get("params", [])
        if not isinstance(params, list):
            raise ValueError("params 必须是数组")

        valid_in_values = {"path", "query", "body", "header"}
        valid_types = {"string", "integer", "number", "boolean", "object"}
        path_params_defined = set()

        for i, p in enumerate(params):
            if not isinstance(p, dict):
                raise ValueError(f"params[{i}] 必须是对象")
            if not p.get("name"):
                raise ValueError(f"params[{i}] 缺少 name 字段")
            p_in = p.get("in", "")
            if p_in not in valid_in_values:
                raise ValueError(f"params[{i}].in 必须是 {'/'.join(valid_in_values)} 之一")
            p_type = p.get("type", "")
            if p_type not in valid_types:
                raise ValueError(f"params[{i}].type 必须是 {'/'.join(valid_types)} 之一")
            if p_in == "path":
                path_params_defined.add(p.get("name"))

        # 验证 URL 中的路径占位符都有对应的 path 参数定义
        url = config.get("url", "")
        path_placeholders = set(re.findall(r"\{(\w+)\}", url))
        missing = path_placeholders - path_params_defined
        if missing:
            raise ValueError(f"URL 中的占位符 {missing} 缺少对应的 path 参数定义")

        # 验证 response.extract
        response = config.get("response", {})
        if response and response.get("extract") is not None:
            if not isinstance(response["extract"], str):
                raise ValueError("response.extract 必须是字符串")
