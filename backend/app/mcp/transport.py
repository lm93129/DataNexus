"""MCP SSE Transport 挂载模块

将 MCP server 通过 SSE（Server-Sent Events）协议暴露为 HTTP 端点，
并在 SSE 连接建立时执行身份鉴权。

路由结构：
  GET  /mcp/sse        — 建立 SSE 长连接（鉴权入口）
  POST /mcp/messages/  — 客户端发送 JSON-RPC 消息
"""
import asyncio
import contextvars
import logging

from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.mcp.server import mcp_server, mcp_user_context

logger = logging.getLogger(__name__)

# SSE transport 实例，指定客户端 POST 消息的路径（相对于 /mcp mount 点）
sse_transport = SseServerTransport("/messages/")

# MCP SSE 并发连接限制
MAX_SSE_CONNECTIONS = 5
_connection_count = 0


async def handle_sse(request: Request):
    """处理 SSE 连接请求

    流程：
    1. 并发连接数检查
    2. 鉴权：验证 Bearer Token 或 X-API-Key
    3. 在独立上下文中运行 MCP server（防止 ContextVar 泄漏）
    """
    from app.core.database import async_session_factory
    from app.mcp.auth import authenticate_mcp_request

    # 并发连接限制：检查当前连接数
    global _connection_count
    if _connection_count >= MAX_SSE_CONNECTIONS:
        return JSONResponse(
            status_code=503,
            content={"detail": f"MCP SSE 并发连接已达上限（{MAX_SSE_CONNECTIONS}），请稍后重试"},
        )

    _connection_count += 1
    try:
        # 鉴权：连接建立前必须通过身份验证
        async with async_session_factory() as db:
            user = await authenticate_mcp_request(request, db)
            logger.info("MCP SSE 连接已鉴权，用户 ID: %s", user.id)

        # 在独立上下文副本中运行，防止并发连接间 ContextVar 泄漏
        ctx = contextvars.copy_context()
        ctx.run(mcp_user_context.set, {
            "user_id": user.id,
            "username": user.name,
            "role": user.role,
            "identity_type": user.identity_type,
        })

        # 在隔离上下文中运行 MCP server（显式传递 context 确保 Task 全生命周期继承）
        task = asyncio.create_task(_run_mcp_session(request), context=ctx)
        await task
    finally:
        _connection_count -= 1


async def _run_mcp_session(request: Request):
    """在隔离的 ContextVar 上下文中运行 MCP SSE 会话"""
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
