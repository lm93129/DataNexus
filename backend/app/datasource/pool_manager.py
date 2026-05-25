from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.datasource import Datasource


class PoolManager:
    """管理多数据源的连接池，按数据源ID路由"""

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

    def __init__(self):
        self._engines: dict[int, AsyncEngine] = {}

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
        driver = self.DRIVER_MAP.get(ds.type, "postgresql+asyncpg")
        username = quote_plus(ds.username)
        pwd = quote_plus(password)
        return f"{driver}://{username}:{pwd}@{ds.host}:{ds.port}/{ds.database}"

    async def get_engine(self, ds: Datasource, password: str) -> AsyncEngine:
        if ds.id not in self._engines:
            url = self._build_url(ds, password)
            self._engines[ds.id] = create_async_engine(url, pool_size=5, max_overflow=10)
        return self._engines[ds.id]

    async def remove_engine(self, ds_id: int):
        if ds_id in self._engines:
            await self._engines[ds_id].dispose()
            del self._engines[ds_id]

    async def dispose_all(self):
        for engine in self._engines.values():
            await engine.dispose()
        self._engines.clear()


pool_manager = PoolManager()
