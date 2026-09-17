"""Add cow telemetry and alert tables for the Jetson collector.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-10 12:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS jetson_telemetry'))

    op.create_table(
        'cow_telemetry_history',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cow_id', sa.Integer(), nullable=False),
        sa.Column('camera_id', sa.String(64), nullable=False, server_default=''),
        sa.Column('body_temperature', sa.Numeric(10, 3), nullable=True),
        sa.Column('body_temperature_observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('milk_yield', sa.Numeric(10, 3), nullable=True),
        sa.Column('milk_yield_observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('milk_reduction_ratio', sa.Numeric(10, 5), nullable=True),
        sa.Column('milk_reduction_ratio_observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('elevated_temp_alert', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('elevated_temp_alert_observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('milk_alert', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('milk_alert_observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('health_alert', sa.String(64), nullable=False, server_default='NONE'),
        sa.Column('health_alert_observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('time', 'cow_id'),
        schema='jetson_telemetry',
    )
    op.create_index(
        'idx_cow_telemetry_camera_time',
        'cow_telemetry_history',
        ['camera_id', 'time'],
        schema='jetson_telemetry',
    )

    op.create_table(
        'cow_alert_events',
        sa.Column('cow_id', sa.Integer(), nullable=False),
        sa.Column('camera_id', sa.String(64), nullable=False, server_default=''),
        sa.Column('alert_type', sa.String(32), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('peak_temperature', sa.Numeric(10, 3), nullable=True),
        sa.Column('milk_yield', sa.Numeric(10, 3), nullable=True),
        sa.Column('milk_reduction_ratio', sa.Numeric(10, 5), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('cow_id', 'alert_type', 'start_time'),
        schema='jetson_telemetry',
    )
    op.create_index(
        'idx_cow_alert_events_camera_time',
        'cow_alert_events',
        ['camera_id', 'start_time'],
        schema='jetson_telemetry',
    )
    op.create_index(
        'idx_cow_alert_events_type_time',
        'cow_alert_events',
        ['alert_type', 'start_time'],
        schema='jetson_telemetry',
    )


def downgrade() -> None:
    op.drop_index(
        'idx_cow_alert_events_type_time',
        table_name='cow_alert_events',
        schema='jetson_telemetry',
    )
    op.drop_index(
        'idx_cow_alert_events_camera_time',
        table_name='cow_alert_events',
        schema='jetson_telemetry',
    )
    op.drop_table('cow_alert_events', schema='jetson_telemetry')
    op.drop_index(
        'idx_cow_telemetry_camera_time',
        table_name='cow_telemetry_history',
        schema='jetson_telemetry',
    )
    op.drop_table('cow_telemetry_history', schema='jetson_telemetry')
