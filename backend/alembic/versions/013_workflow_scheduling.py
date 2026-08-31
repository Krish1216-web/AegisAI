"""workflow scheduling

Revision ID: 013_workflow_scheduling
Revises: 012_workflow_approval_governance
Create Date: 2026-08-31 14:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013_workflow_scheduling'
down_revision = '012_workflow_approval_governance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_schedules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schedule_type', sa.String(length=50), nullable=False, server_default='cron'),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('workflow_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('concurrency_policy', sa.String(length=50), nullable=False, server_default='skip'),
        sa.Column('misfire_policy', sa.String(length=50), nullable=False, server_default='run_once'),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_execution_id', sa.UUID(), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_execution_id'], ['workflow_executions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_schedules_workflow_id'), 'workflow_schedules', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_workspace_id'), 'workflow_schedules', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_created_by'), 'workflow_schedules', ['created_by'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_name'), 'workflow_schedules', ['name'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_schedule_type'), 'workflow_schedules', ['schedule_type'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_status'), 'workflow_schedules', ['status'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_next_run_at'), 'workflow_schedules', ['next_run_at'], unique=False)
    op.create_index(op.f('ix_workflow_schedules_last_execution_id'), 'workflow_schedules', ['last_execution_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_schedules_last_execution_id'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_next_run_at'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_status'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_schedule_type'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_name'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_created_by'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_workspace_id'), table_name='workflow_schedules')
    op.drop_index(op.f('ix_workflow_schedules_workflow_id'), table_name='workflow_schedules')
    op.drop_table('workflow_schedules')
