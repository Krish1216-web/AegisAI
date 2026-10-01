"""background_jobs

Revision ID: 019_background_jobs
Revises: 018_notifications_realtime
Create Date: 2026-10-01 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = '019_background_jobs'
down_revision = '018_notifications_realtime'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), server_default='queued', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='50', nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('idempotency_key', sa.String(255), nullable=True),
        sa.Column('correlation_id', sa.String(255), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='3', nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('error_category', sa.String(50), nullable=True),
        sa.Column('worker_id', sa.String(100), nullable=True),
        sa.Column('lock_token', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_bgjobs_workspace_id', 'background_jobs', ['workspace_id'])
    op.create_index('ix_bgjobs_created_by', 'background_jobs', ['created_by'])
    op.create_index('ix_bgjobs_job_type', 'background_jobs', ['job_type'])
    op.create_index('ix_bgjobs_status', 'background_jobs', ['status'])
    op.create_index('ix_bgjobs_priority', 'background_jobs', ['priority'])
    op.create_index('ix_bgjobs_idempotency_key', 'background_jobs', ['idempotency_key'])
    op.create_index('ix_bgjobs_correlation_id', 'background_jobs', ['correlation_id'])
    op.create_index('ix_bgjobs_scheduled_at', 'background_jobs', ['scheduled_at'])
    op.create_index('ix_bgjobs_heartbeat_at', 'background_jobs', ['heartbeat_at'])
    op.create_index('ix_bgjobs_next_retry_at', 'background_jobs', ['next_retry_at'])
    op.create_index('ix_bgjobs_worker_id', 'background_jobs', ['worker_id'])
    op.create_index('ix_bgjobs_status_scheduled', 'background_jobs', ['status', 'scheduled_at'])
    op.create_index('ix_bgjobs_ws_status', 'background_jobs', ['workspace_id', 'status'])
    op.create_index('ix_bgjobs_ws_idempotency', 'background_jobs', ['workspace_id', 'idempotency_key'])
    op.create_index('ix_bgjobs_stale_detection', 'background_jobs', ['status', 'heartbeat_at'])

def downgrade():
    op.drop_table('background_jobs')
