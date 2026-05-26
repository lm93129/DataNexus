import asyncio
import logging
from collections import OrderedDict
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.datasource import Datasource

logger = logging.getLogger(__name__)

MAX_POOL_SIZE = 50


class PoolManager:
    """管理多数据源的连接池，按数据源ID路由，LRU 淘汰策略"""

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
        self._engines: OrderedDict[int, AsyncEngine] = OrderedDict()
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    def _check_driver(self, ds_type: str):
        """检查对应驱动是否已安装。

        postgresql 使用 asyncpg，属于核心依赖，始终跳过检查。
        其余类型（mysql/mssql/oracle）为可选依赖，未安装时抛出 RuntimeError。
        """
        if ds_type == "postgresql":
            # asyncpg 是核心依赖，不做运行时检查
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
        return f"{driver}://{username}:{pwd}@{ds.host}:{ds.port}/{ds.database}"

    async def get_engine(self, ds: Datasource, password: str) -> AsyncEngine:
        async with self._lock:
            if ds.id in self._engines:
                # LRU：移到末尾表示最近使用
                self._engines.move_to_end(ds.id)
                return self._engines[ds.id]

            # 淘汰最久未使用的 engine
            while len(self._engines) >= self._maxsize:
                evicted_id, evicted_engine = self._engines.popitem(last=False)
                logger.info("LRU 淘汰连接池: datasource_id=%s", evicted_id)
                await evicted_engine.dispose()

            url = self._build_url(ds, password)
            self._engines[ds.id] = create_async_engine(
                url, pool_size=5, max_overflow=10, pool_pre_ping=True
            )
            return self._engines[ds.id]

    async def invalidate(self, ds_id: int):
        """数据源凭证变更时调用，清除缓存的 engine 以强制重建连接"""
        await self.remove_engine(ds_id)

    async def remove_engine(self, ds_id: int):
        if ds_id in self._engines:
            await self._engines[ds_id].dispose()
            del self._engines[ds_id]

    async def dispose_all(self):
        for engine in self._engines.values():
            await engine.dispose()
        self._engines.clear()


pool_manager = PoolManager()
