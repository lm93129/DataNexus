"""测试 MCP list_datasources 工具

使用独立的 SSE 读取协程 + POST 发送，避免 httpx stream consumed 问题。

流程：登录 → SSE 连接 → initialize → tools/list → list_datasources
"""
import asyncio
import json
import uuid

import httpx

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"
# API Key 认证（优先使用，跳过登录步骤）
API_KEY = "dnx_XKkYU_aqDqJb0D8d_SptacF7szIPkkcznSy-Ko48S44"


class McpSseClient:
    """简易 MCP SSE 客户端"""

    def __init__(self, base_url: str, auth_headers: dict):
        self.base_url = base_url
        self.headers = auth_headers
        self.messages_url = None
        self._pending: dict[str, asyncio.Future] = {}
        self._sse_task = None

    async def connect(self):
        """建立 SSE 连接并启动后台读取"""
        self._client = httpx.AsyncClient(timeout=60)
        self._response = await self._client.send(
            self._client.build_request("GET", f"{self.base_url}/mcp/sse", headers=self.headers),
            stream=True,
        )
        if self._response.status_code != 200:
            raise RuntimeError(f"SSE 连接失败: {self._response.status_code}")

        # 启动后台 SSE 读取
        self._sse_task = asyncio.create_task(self._read_sse())

        # 等待获取 messages endpoint
        while self.messages_url is None:
            await asyncio.sleep(0.05)

    async def _read_sse(self):
        """后台读取 SSE 事件流"""
        current_event = ""
        async for line in self._response.aiter_lines():
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:].strip()
                if current_event == "endpoint":
                    # 修正路径：SSE transport 返回的路径可能有前缀问题
                    self.messages_url = f"{self.base_url}{data_str}"
                elif current_event == "message":
                    try:
                        data = json.loads(data_str)
                        msg_id = data.get("id")
                        if msg_id and msg_id in self._pending:
                            self._pending[msg_id].set_result(data)
                    except json.JSONDecodeError:
                        pass
                current_event = ""

    async def send_request(self, method: str, params: dict = None) -> dict:
        """发送 JSON-RPC 请求并等待响应"""
        msg_id = str(uuid.uuid4())
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            msg["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future

        resp = await self._client.post(self.messages_url, json=msg, headers=self.headers)
        if resp.status_code not in (200, 202):
            del self._pending[msg_id]
            raise RuntimeError(f"POST 失败: {resp.status_code} {resp.text}")

        result = await asyncio.wait_for(future, timeout=15)
        del self._pending[msg_id]
        return result

    async def send_notification(self, method: str, params: dict = None):
        """发送 JSON-RPC 通知（无响应）"""
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        await self._client.post(self.messages_url, json=msg, headers=self.headers)

    async def close(self):
        if self._sse_task:
            self._sse_task.cancel()
        await self._response.aclose()
        await self._client.aclose()


async def main():
    # 确定认证 headers
    if API_KEY:
        print("[1] 使用 API Key 认证...")
        auth_headers = {"X-API-Key": API_KEY}
    else:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as http:
            print("[1] 登录...")
            resp = await http.post("/api/v1/auth/login", json={
                "username": USERNAME,
                "password": PASSWORD,
            })
            if resp.status_code != 200:
                print(f"  失败: {resp.status_code} {resp.text}")
                return
            token = resp.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}
            print(f"  成功")

    # 2. MCP 连接
    print("\n[2] 建立 MCP SSE 连接...")
    mcp = McpSseClient(BASE_URL, auth_headers)
    await mcp.connect()
    print(f"  endpoint: {mcp.messages_url}")

    try:
        # 3. 握手
        print("\n[3] MCP 握手...")
        result = await mcp.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        })
        server_info = result.get("result", {}).get("serverInfo", {})
        print(f"  server: {server_info}")

        await mcp.send_notification("notifications/initialized")
        print("  握手完成")

        # 4. 工具列表
        print("\n[4] 获取工具列表...")
        result = await mcp.send_request("tools/list", {})
        tools = result.get("result", {}).get("tools", [])
        print(f"  工具数量: {len(tools)}")
        for t in tools:
            print(f"    - {t['name']}: {t['description'][:60]}")

        # 5. 调用 list_datasources
        print("\n[5] 调用 list_datasources...")
        result = await mcp.send_request("tools/call", {
            "name": "list_datasources",
            "arguments": {},
        })
        content = result.get("result", {}).get("content", [])
        print("  返回结果:")
        for c in content:
            print(f"    {c.get('text', '')}")

    finally:
        await mcp.close()

    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
