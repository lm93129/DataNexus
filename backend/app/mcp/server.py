"""MCP Server 定义与工具处理

提供三个工具：
- get_database_schema：获取数据库元数据
- query_database：执行只读 SQL 查询
- call_custom_api：调用预注册的自定义 API

每次工具调用均写入审计日志。
"""
import json
from contextvars import ContextVar

from mcp.server import Server
from mcp.types import TextContent, Tool

from app.core.permissions import _has_permission

mcp_server = Server("datanexus")

# 存储当前 SSE 连接的认证用户信息，由 transport.py 在鉴权后设置
mcp_user_context: ContextVar[dict] = ContextVar("mcp_user_context", default={"user_id": 0, "username": "anonymous", "role": "viewer", "identity_type": "user"})

# MCP 工具名 -> 所需权限映射
TOOL_PERMISSION_MAP: dict[str, str] = {
    "get_database_schema": "metadata:read",
    "query_database": "query:execute",
    "call_custom_api": "custom_api:read",
}


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """返回 MCP server 支持的工具列表"""
    return [
        Tool(
            name="get_database_schema",
            description="获取数据库元数据：表名列表或指定表的字段结构",
            inputSchema={
                "type": "object",
                "properties": {
                    "datasource_id": {"type": "integer", "description": "数据源ID"},
                    "table_name": {"type": "string", "description": "表名（可选）"},
                },
                "required": ["datasource_id"],
            },
        ),
        Tool(
            name="query_database",
            description="执行安全的只读SQL查询，仅支持SELECT语句",
            inputSchema={
                "type": "object",
                "properties": {
                    "datasource_id": {"type": "integer", "description": "数据源ID"},
                    "sql": {"type": "string", "description": "SELECT查询语句"},
                },
                "required": ["datasource_id", "sql"],
            },
        ),
        Tool(
            name="call_custom_api",
            description="调用平台已封装的内部业务系统API",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_name": {"type": "string", "description": "API名称"},
                    "params": {"type": "object", "description": "调用参数"},
                },
                "required": ["api_name"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """统一工具调用入口，含权限校验和审计日志"""
    from app.core.database import async_session_factory
    from app.services.audit import AuditService

    # 从 ContextVar 获取当前连接的认证用户身份
    user_ctx = mcp_user_context.get()
    identity_id = user_ctx["user_id"]
    role = user_ctx["role"]
    identity_type = f"mcp_{user_ctx['identity_type']}"

    # 防御性检查：未鉴权连接不允许调用工具
    if identity_id == 0:
        return [TextContent(type="text", text="鉴权失败：未识别的用户身份，请重新连接")]

    # 权限校验：根据工具名检查角色权限
    required_perm = TOOL_PERMISSION_MAP.get(name)
    if required_perm and not _has_permission(role, required_perm):
        # 权限拒绝写审计日志
        async with async_session_factory() as db:
            audit = AuditService(db)
            await audit.log(
                identity_id=identity_id,
                identity_type=identity_type,
                action=f"mcp_call:{name}",
                resource=json.dumps(arguments, ensure_ascii=False)[:200],
                status="denied",
            )
        return [TextContent(type="text", text=f"权限不足：角色 {role} 无权执行 {name}（需要 {required_perm}）")]

    async with async_session_factory() as db:
        result = await _dispatch_tool(db, name, arguments, identity_id)

        # 判断调用是否成功（结果文本中含"失败"则视为 error）
        call_status = (
            "error"
            if any("失败" in r.text for r in result)
            else "success"
        )

        # 写入审计日志
        audit = AuditService(db)
        await audit.log(
            identity_id=identity_id,
            identity_type=identity_type,
            action=f"mcp_call:{name}",
            resource=json.dumps(arguments, ensure_ascii=False)[:200],
            status=call_status,
        )

        return result


async def _dispatch_tool(
    db, name: str, arguments: dict, identity_id: int
) -> list[TextContent]:
    """根据工具名称分发到对应处理函数"""
    if name == "get_database_schema":
        return await _handle_get_schema(db, arguments)
    elif name == "query_database":
        return await _handle_query(db, arguments, identity_id)
    elif name == "call_custom_api":
        return await _handle_custom_api(db, arguments)
    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def _handle_get_schema(db, arguments: dict) -> list[TextContent]:
    """处理 get_database_schema 工具调用"""
    from app.services.metadata import MetadataService

    service = MetadataService(db)
    datasource_id = arguments["datasource_id"]
    table_name = arguments.get("table_name")

    if table_name:
        # 查询指定表的字段结构
        table_meta = await service.get_table_by_name(datasource_id, table_name)
        if not table_meta:
            return [TextContent(type="text", text=f"表 {table_name} 不存在或已被屏蔽")]
        columns = await service.get_columns(table_meta.id)
        col_info = "\n".join(
            f"  - {c.column_name} ({c.data_type}){' [PK]' if c.is_primary_key else ''}"
            f"{f' -- {c.column_comment}' if c.column_comment else ''}"
            for c in columns
        )
        return [TextContent(type="text", text=f"表 {table_name} 字段结构:\n{col_info}")]
    else:
        # 返回所有可用表名
        tables = await service.get_tables(datasource_id)
        table_list = "\n".join(
            f"  - {t.table_name}{f' -- {t.table_comment}' if t.table_comment else ''}"
            for t in tables
        )
        return [TextContent(type="text", text=f"可用表列表:\n{table_list}")]


async def _handle_query(
    db, arguments: dict, identity_id: int
) -> list[TextContent]:
    """处理 query_database 工具调用"""
    from app.services.query import QueryService
    from app.services.rate_limit import RateLimitService

    # 动态限流检查
    rl_service = RateLimitService(db)
    deny_reason = await rl_service.check_rate_limit(
        user_id=identity_id, datasource_id=arguments.get("datasource_id")
    )
    if deny_reason:
        return [TextContent(type="text", text=f"请求被限流: {deny_reason}")]

    # 获取动态最大行数
    dynamic_max_rows = await rl_service.get_max_rows(
        user_id=identity_id, datasource_id=arguments.get("datasource_id")
    )

    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=arguments["datasource_id"],
        sql=arguments["sql"],
        identity_id=identity_id,
        max_rows_override=dynamic_max_rows,
    )

    # 记录请求
    await rl_service.record_request(
        user_id=identity_id, datasource_id=arguments.get("datasource_id")
    )

    if not result["success"]:
        return [TextContent(type="text", text=f"查询失败: {result['error']}")]
    return [
        TextContent(
            type="text",
            text=json.dumps(result["data"], ensure_ascii=False, default=str),
        )
    ]


async def _handle_custom_api(db, arguments: dict) -> list[TextContent]:
    """调用预注册的自定义 API

    根据 mode 分发：
    - low_code: 使用精细执行引擎（参数路由、认证注入、响应提取）
    - custom: 保持原有简单转发逻辑
    """
    import httpx
    from sqlalchemy import select

    from app.models.custom_api import CustomApi
    from app.services.custom_api import CustomApiService

    api_name = arguments.get("api_name")
    params = arguments.get("params", {})

    # 查询已启用的 API 配置
    result = await db.execute(
        select(CustomApi).where(
            CustomApi.name == api_name,
            CustomApi.is_active == True,  # noqa: E712
        )
    )
    api = result.scalar_one_or_none()
    if not api:
        return [TextContent(type="text", text=f"API '{api_name}' 不存在或未启用")]

    config = json.loads(api.config_json)

    # low_code 模式使用精细执行引擎
    if api.mode == "low_code":
        service = CustomApiService(db)
        call_result = await service._execute_low_code(config, params)
        if call_result.get("success"):
            data = call_result.get("data", "")
            text = json.dumps(data, ensure_ascii=False, default=str) if not isinstance(data, str) else data
            return [TextContent(type="text", text=text[:5000])]
        else:
            return [TextContent(type="text", text=f"API调用失败: {call_result.get('message', '')}")]

    # custom 模式保持原有逻辑
    url = config.get("url", "")
    method = config.get("method", "GET").upper()
    headers = config.get("headers", {})

    # SSRF 防护：阻止访问内网地址
    from app.services.custom_api import _is_ssrf_target
    if _is_ssrf_target(url):
        return [TextContent(type="text", text="API调用失败: 目标地址不允许访问（SSRF防护）")]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, params=params, headers=headers)
            else:
                resp = await client.request(method, url, json=params, headers=headers)
            return [TextContent(type="text", text=resp.text[:5000])]
    except Exception as e:
        return [TextContent(type="text", text=f"API调用失败: {str(e)}")]
