import logging
from pathlib import Path
from contextlib import asynccontextmanager

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import inspect, select, text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.permissions import PERMISSION_MATRIX
from app.core.security import hash_password
from app.mcp.transport import mcp_routes
from app.middleware.rate_limit import limiter
from app.models import Base
from app.models.user import Role, RolePermission, User, UserRole

logger = logging.getLogger(__name__)

ROLE_DESCRIPTIONS = {
    "admin": "系统管理员，拥有全部权限",
    "analyst": "分析师，可执行查询和管理数据源",
    "viewer": "查看者，仅可浏览元数据和查看日志",
}


def _database_has_no_tables(connection) -> bool:
    return not inspect(connection).get_table_names()


def _get_alembic_head_revision() -> str:
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    return ScriptDirectory.from_config(alembic_config).get_current_head()


def _stamp_alembic_head(connection) -> None:
    head_revision = _get_alembic_head_revision()
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
    )
    connection.execute(text("DELETE FROM alembic_version"))
    connection.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
        {"version_num": head_revision},
    )


async def create_tables_for_empty_database() -> None:
    """仅在平台库完全为空时创建表结构；已有表时交由 Alembic 迁移维护。"""
    async with engine.begin() as connection:
        is_empty_database = await connection.run_sync(_database_has_no_tables)
        if not is_empty_database:
            return

        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_stamp_alembic_head)
        logger.info("检测到空数据库，已创建表结构并标记 Alembic head")


async def init_roles_and_permissions(session) -> dict[str, Role]:
    role_by_name: dict[str, Role] = {}
    for role_name, description in ROLE_DESCRIPTIONS.items():
        role_query = await session.execute(select(Role).where(Role.name == role_name))
        role = role_query.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, description=description)
            session.add(role)
        role_by_name[role_name] = role

    await session.flush()

    for role_name, permissions in PERMISSION_MATRIX.items():
        role = role_by_name[role_name]
        for permission_name in permissions:
            resource_type, action = permission_name.split(":", 1)
            permission_query = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.resource_type == resource_type,
                    RolePermission.resource_id == 0,
                    RolePermission.permission == action,
                )
            )
            if permission_query.scalar_one_or_none() is None:
                session.add(
                    RolePermission(
                        role_id=role.id,
                        resource_type=resource_type,
                        resource_id=0,
                        permission=action,
                    )
                )

    return role_by_name


async def init_default_admin():
    """启动时检查并创建默认管理员账号、角色和权限。"""
    async with async_session_factory() as session:
        role_by_name = await init_roles_and_permissions(session)

        admin_query = await session.execute(select(User).where(User.name == "admin"))
        admin_user = admin_query.scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                name="admin",
                identity_type="user",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()

            logger.info("已创建默认管理员账号: admin（请立即修改默认密码）")
        elif admin_user.role != "admin":
            admin_user.role = "admin"

        admin_role = role_by_name["admin"]
        user_role_query = await session.execute(
            select(UserRole).where(
                UserRole.user_id == admin_user.id,
                UserRole.role_id == admin_role.id,
            )
        )
        if user_role_query.scalar_one_or_none() is None:
            session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables_for_empty_database()
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
