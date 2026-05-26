"""phase2 schema updates: blacklist, rate_limits rebuild, alert tables, query_history

Revision ID: a1b2c3d4e5f6
Revises: 30c32a1ad0b2
Create Date: 2026-05-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '30c32a1ad0b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. datasources 表新增黑名单字段
    op.add_column('datasources', sa.Column('table_blacklist', sa.Text(), nullable=True, server_default='[]'))
    op.add_column('datasources', sa.Column('column_blacklist', sa.Text(), nullable=True, server_default='[]'))

    # 2. 重建 rate_limits 表（旧结构: identity_id/max_qps/max_daily_calls/max_rows_per_query）
    op.drop_table('rate_limits')
    op.create_table('rate_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False, server_default='global'),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('max_per_minute', sa.Integer(), nullable=True),
        sa.Column('max_per_hour', sa.Integer(), nullable=True),
        sa.Column('max_per_day', sa.Integer(), nullable=True),
        sa.Column('max_rows_per_query', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. 新增 alert_rules 表
    op.create_table('alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.String(length=30), nullable=False),
        sa.Column('threshold_config', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('scope', sa.String(length=20), nullable=False, server_default='global'),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('suppress_minutes', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. 新增 alert_records 表
    op.create_table('alert_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False, index=True),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.String(length=30), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_records_rule_id', 'alert_records', ['rule_id'])

    # 5. 新增 query_history 表（原迁移 30c32a1ad0b2 为空）
    op.create_table('query_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('datasource_id', sa.Integer(), sa.ForeignKey('datasources.id'), nullable=False),
        sa.Column('sql', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('query_history')
    op.drop_index('ix_alert_records_rule_id', table_name='alert_records')
    op.drop_table('alert_records')
    op.drop_table('alert_rules')

    # 恢复旧 rate_limits 结构
    op.drop_table('rate_limits')
    op.create_table('rate_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identity_id', sa.Integer(), nullable=False),
        sa.Column('max_qps', sa.Integer(), nullable=False),
        sa.Column('max_daily_calls', sa.Integer(), nullable=False),
        sa.Column('max_rows_per_query', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.drop_column('datasources', 'column_blacklist')
    op.drop_column('datasources', 'table_blacklist')
