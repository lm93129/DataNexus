"""MCP SSE Transport 挂载模块

将 MCP server 通过 SSE（Server-Sent Events）协议暴露为 HTTP 端点，
并在 SSE 连接建立时执行身份鉴权。

路由结构：
  GET  /mcp/sse        — 建立 SSE 长连接（鉴权入口）
  POST /mcp/messages/  — 客户端发送 JSON-RPC 消息
"""
import logging

from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route

from app.mcp.server import mcp_server, mcp_user_context

logger = logging.getLogger(__name__)

# SSE transport 实例，指定客户端 POST 消息的路径
sse_transport = SseServerTransport("/mcp/messages/")


async def handle_sse(request: Request):
    """处理 SSE 连接请求

    流程：
    1. 鉴权：验证 Bearer Token 或 X-API-Key
    2. 将用户身份写入 ContextVar
    3. 建立 SSE 流
    4. 运行 MCP server（阻塞直到连接断开）
    """
    from app.core.database import async_session_factory
    from app.mcp.auth import authenticate_mcp_request

    # 鉴权：连接建立前必须通过身份验证
    async with async_session_factory() as db:
        user = await authenticate_mcp_request(request, db)
        logger.info("MCP SSE 连接已鉴权，用户 ID: %s", user.id)

    # 将认证用户信息写入上下文，供 call_tool 使用
    mcp_user_context.set({"user_id": user.id, "username": user.username, "role": user.role})

    # 建立 SSE 流并运行 MCP server
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        read_stream, write_stream = streams
        init_options = mcp_server.create_initialization_options()
        await mcp_server.run(read_stream, write_stream, init_options)


# 导出 Starlette Mount，供 main.py 挂载到 FastAPI app
mcp_routes = Mount(
    "/mcp",
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)
