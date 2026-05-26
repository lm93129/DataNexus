import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.api.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.mcp.transport import mcp_routes
from app.middleware.rate_limit import limiter
from app.models.user import Role, User, UserRole

logger = logging.getLogger(__name__)


async def init_default_admin():
    """启动时检查并创建默认管理员账号和角色"""
    async with async_session_factory() as session:
        # 初始化默认角色
        for role_name, desc in [
            ("admin", "系统管理员，拥有全部权限"),
            ("analyst", "分析师，可执行查询和管理数据源"),
            ("viewer", "查看者，仅可浏览元数据和查看日志"),
        ]:
            result = await session.execute(select(Role).where(Role.name == role_name))
            if not result.scalar_one_or_none():
                session.add(Role(name=role_name, description=desc))

        await session.flush()

        # 检查是否存在管理员用户
        result = await session.execute(select(User).where(User.name == "admin"))
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                name="admin",
                identity_type="user",
                password_hash=hash_password("admin123"),
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()

            # 关联 admin 角色
            role_result = await session.execute(select(Role).where(Role.name == "admin"))
            admin_role = role_result.scalar_one()
            session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))

            logger.info("已创建默认管理员账号: admin（请立即修改默认密码）")

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_default_admin()
    yield
    # 关闭时清理所有数据源连接池
    from app.datasource.pool_manager import pool_manager
    await pool_manager.dispose_all()
    logger.info("所有数据源连接池已清理")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# 限流中间件
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
app.include_router(api_router)

# 挂载 MCP SSE 传输路由（/mcp/sse 和 /mcp/messages/）
app.routes.append(mcp_routes)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理：生产环境隐藏内部错误详情"""
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    if settings.debug:
        detail = str(exc)
    else:
        detail = "服务器内部错误，请联系管理员"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/health")
async def health_check():
    """健康检查：含数据库连通性"""
    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(select(1))
            db_ok = True
    except Exception:
        pass
    status = "ok" if db_ok else "degraded"
    return {"status": status, "service": settings.app_name, "database": "connected" if db_ok else "disconnected"}
