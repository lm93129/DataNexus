"""add api_key_prefix to users table

Revision ID: f7a8b9c0d1e2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新增 api_key_prefix 列，用于 O(1) API Key 前缀索引查找
    op.add_column('users', sa.Column('api_key_prefix', sa.String(length=8), nullable=True))
    op.create_index('ix_users_api_key_prefix', 'users', ['api_key_prefix'])

    # 回填已有 API Key 用户的前缀（从加密存储的 key 解密取前8位）
    # 注意：此步骤需要在应用层执行，因为密钥解密依赖 app 配置
    # 可通过以下脚本完成回填：
    # python -c "
    # import asyncio
    # from app.core.database import async_session_factory
    # from app.core.security import decrypt_api_key
    # from app.models.user import User
    # from sqlalchemy import select, update
    #
    # async def backfill():
    #     async with async_session_factory() as db:
    #         result = await db.execute(
    #             select(User).where(User.api_key_encrypted.isnot(None), User.api_key_prefix.is_(None))
    #         )
    #         for user in result.scalars().all():
    #             try:
    #                 raw_key = decrypt_api_key(user.api_key_encrypted)
    #                 user.api_key_prefix = raw_key[:8]
    #             except Exception:
    #                 pass
    #         await db.commit()
    #
    # asyncio.run(backfill())
    # "


def downgrade() -> None:
    op.drop_index('ix_users_api_key_prefix', table_name='users')
    op.drop_column('users', 'api_key_prefix')
