import asyncio
import logging
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Union
from urllib.parse import quote_plus

from sqlalchemy import Engine, Connection, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.datasource import Datasource

logger = logging.getLogger(__name__)

MAX_POOL_SIZE = 50

_oracle_thick_initialized = False


def _ensure_oracle_thick():
    """确保 Oracle thick 模式已初始化（仅调用一次）"""
    global _oracle_thick_initialized
    if _oracle_thick_initialized:
        return
    from app.core.config import settings
    import oracledb
    try:
        lib_dir = settings.oracle_client_dir
        if lib_dir:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        else:
            oracledb.init_oracle_client()
        logger.info("Oracle thick 模式已启用: %s", lib_dir or "系统 PATH")
    except oracledb.ProgrammingError:
        pass
    _oracle_thick_initialized = True


class _SyncConnWrapper:
    """将同步 Connection 包装为类 async 接口，供 Oracle thick 模式使用"""

    def __init__(self, conn: Connection):
        self._conn = conn

    async def execute(self, stmt, *args, **kwargs):
        return await asyncio.to_thread(self._conn.execute, stmt, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@asynccontextmanager
async def async_connect(engine: Union[AsyncEngine, Engine]):
    """统一的 async 连接上下文管理器，兼容 sync/async engine"""
    if isinstance(engine, AsyncEngine):
        async with engine.connect() as conn:
            yield conn
    else:
        conn = await asyncio.to_thread(engine.connect)
        try:
            yield _SyncConnWrapper(conn)
        finally:
            await asyncio.to_thread(conn.close)


class PoolManager:
    """管理多数据源的连接池，按数据源ID路由，LRU 淘汰策略

    Oracle 使用同步 engine（thick 模式不支持 async），其他数据源使用 async engine。
    """

    DRIVER_MAP = {
        "mysql": "mysql+aiomysql",
        "postgresql": "postgresql+asyncpg",
        "mssql": "mssql+aioodbc",
        "oracle": "oracle+oracledb",
    }

    DRIVER_PACKAGES = {
        "mysql": "aiomysql",
        "postgresql": "asyncpg",
        "mssql": "aioodbc",
        "oracle": "oracledb",
    }

    def __init__(self, maxsize: int = MAX_POOL_SIZE):
        self._engines: OrderedDict[int, Union[AsyncEngine, Engine]] = OrderedDict()
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    def _check_driver(self, ds_type: str):
        """检查对应驱动是否已安装"""
        if ds_type == "postgresql":
            return
        package = self.DRIVER_PACKAGES.get(ds_type)
        if package:
            try:
                __import__(package)
            except ImportError:
                raise RuntimeError(
                    f"数据源类型 '{ds_type}' 需要安装驱动: pip install {package}"
                )

    def _build_url(self, ds: Datasource, password: str) -> str:
        self._check_driver(ds.type)
        driver = self.DRIVER_MAP.get(ds.type)
        if not driver:
            raise ValueError(f"不支持的数据源类型: '{ds.type}'，支持的类型: {list(self.DRIVER_MAP.keys())}")
        username = quote_plus(ds.username)
        pwd = quote_plus(password)
        if ds.type == "oracle":
            return f"{driver}://{username}:{pwd}@{ds.host}:{ds.port}/?service_name={ds.database}"
        return f"{driver}://{username}:{pwd}@{ds.host}:{ds.port}/{ds.database}"

    async def get_engine(self, ds: Datasource, password: str) -> Union[AsyncEngine, Engine]:
        async with self._lock:
            if ds.id in self._engines:
                self._engines.move_to_end(ds.id)
                return self._engines[ds.id]

            while len(self._engines) >= self._maxsize:
                evicted_id, evicted_engine = self._engines.popitem(last=False)
                logger.info("LRU 淘汰连接池: datasource_id=%s", evicted_id)
                if isinstance(evicted_engine, AsyncEngine):
                    await evicted_engine.dispose()
                else:
                    evicted_engine.dispose()

            url = self._build_url(ds, password)
            if ds.type == "oracle":
                _ensure_oracle_thick()
                self._engines[ds.id] = create_engine(
                    url, pool_size=5, max_overflow=10, pool_pre_ping=True
                )
            else:
                self._engines[ds.id] = create_async_engine(
                    url, pool_size=5, max_overflow=10, pool_pre_ping=True
                )
            return self._engines[ds.id]

    async def invalidate(self, ds_id: int):
        """数据源凭证变更时调用，清除缓存的 engine 以强制重建连接"""
        await self.remove_engine(ds_id)

    async def remove_engine(self, ds_id: int):
        if ds_id in self._engines:
            engine = self._engines[ds_id]
            if isinstance(engine, AsyncEngine):
                await engine.dispose()
            else:
                engine.dispose()
            del self._engines[ds_id]

    async def dispose_all(self):
        for engine in self._engines.values():
            if isinstance(engine, AsyncEngine):
                await engine.dispose()
            else:
                engine.dispose()
        self._engines.clear()


pool_manager = PoolManager()
