"""MCP Server 定义与工具处理

提供三个工具：
- get_database_schema：获取数据库元数据
- query_database：执行只读 SQL 查询
- call_custom_api：调用预注册的自定义 API

每次工具调用均写入审计日志。
"""
import json

from mcp.server import Server
from mcp.types import TextContent, Tool

mcp_server = Server("datanexus")


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
    """统一工具调用入口，含审计日志"""
    from app.core.database import async_session_factory
    from app.services.audit import AuditService

    async with async_session_factory() as db:
        # MCP 上下文身份传递待完善，暂用 0 占位
        identity_id = 0

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
            identity_type="mcp",
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

    service = QueryService(db)
    result = await service.execute_query(
        datasource_id=arguments["datasource_id"],
        sql=arguments["sql"],
        identity_id=identity_id,
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

    从 custom_apis 表读取配置（url、method、headers），
    使用 httpx 转发请求并返回响应文本（最多 5000 字符）。
    """
    import httpx
    from sqlalchemy import select

    from app.models.custom_api import CustomApi

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
    url = config.get("url", "")
    method = config.get("method", "GET").upper()
    headers = config.get("headers", {})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, params=params, headers=headers)
            else:
                resp = await client.request(method, url, json=params, headers=headers)
            # 截断响应，避免超大响应占用过多 token
            return [TextContent(type="text", text=resp.text[:5000])]
    except Exception as e:
        return [TextContent(type="text", text=f"API调用失败: {str(e)}")]
