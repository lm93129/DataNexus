from base64 import b64decode, b64encode

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.datasource.pool_manager import pool_manager
from app.models.datasource import Datasource

# 涉及连接信息的字段，变更时需清理旧连接池
CONNECTION_FIELDS = {"host", "port", "database", "username", "password"}


class DatasourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        # 使用 settings.aes_key 派生 Fernet 密钥
        import hashlib
        import base64
        key = hashlib.sha256(settings.aes_key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def _encrypt(self, text: str) -> str:
        return self._fernet.encrypt(text.encode()).decode()

    def _decrypt(self, encrypted: str) -> str:
        return self._fernet.decrypt(encrypted.encode()).decode()

    async def create(self, data: dict) -> Datasource:
        password = data.pop("password")
        ds = Datasource(**data, encrypted_password=self._encrypt(password))
        self.db.add(ds)
        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def list_all(self) -> list[Datasource]:
        result = await self.db.execute(select(Datasource))
        return list(result.scalars().all())

    async def get_by_id(self, ds_id: int) -> Datasource | None:
        return await self.db.get(Datasource, ds_id)

    async def update(self, ds_id: int, data: dict) -> Datasource | None:
        ds = await self.get_by_id(ds_id)
        if not ds:
            return None
        if "password" in data:
            data["encrypted_password"] = self._encrypt(data.pop("password"))
        # 连接信息变更时清理旧连接池
        if CONNECTION_FIELDS & set(data.keys()):
            await pool_manager.remove_engine(ds_id)
        for key, value in data.items():
            if value is not None:
                setattr(ds, key, value)
        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def delete(self, ds_id: int) -> bool:
        ds = await self.get_by_id(ds_id)
        if not ds:
            return False
        await pool_manager.remove_engine(ds_id)
        await self.db.delete(ds)
        await self.db.commit()
        return True

    def get_password(self, ds: Datasource) -> str:
        return self._decrypt(ds.encrypted_password)
