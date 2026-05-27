"""add notification_channels and alert_rule_channels tables

Revision ID: d4e5f6a7b8c9
Revises: f7a8b9c0d1e2
Create Date: 2026-05-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 通知渠道表
    op.create_table('notification_channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('channel_type', sa.String(length=20), nullable=False),
        sa.Column('webhook_url', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 告警规则 ↔ 通知渠道 多对多关联表
    op.create_table('alert_rule_channels',
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['notification_channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('rule_id', 'channel_id')
    )


def downgrade() -> None:
    op.drop_table('alert_rule_channels')
    op.drop_table('notification_channels')
