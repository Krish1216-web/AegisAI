"""Execution persistence tables

Revision ID: 003_execution_persistence
Revises: 002_add_ai_provider_tables
Create Date: 2026-08-11 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_execution_persistence'
down_revision: Union[str, None] = '002_add_ai_provider_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. EXECUTIONS TABLE
    op.create_table(
        'executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('original_request', sa.Text(), nullable=False),
        sa.Column('current_agent', sa.String(length=100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_execution_time', sa.Float(), nullable=True),
        sa.Column('critic_score', sa.Float(), nullable=True),
        sa.Column('response_confidence', sa.Float(), nullable=True),
        sa.Column('final_response', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_executions_user_id'), 'executions', ['user_id'], unique=False)
    op.create_index(op.f('ix_executions_workspace_id'), 'executions', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_executions_status'), 'executions', ['status'], unique=False)

    # 2. ALTER AGENT_EXECUTIONS TABLE
    # Dropping constraints first
    # In sqlite, altering constraints or dropping columns requires recreate under-the-hood.
    # But for PG, we can run direct alters.
    # To support both clean autogeneration/testing and safety, we alter:
    op.add_column('agent_executions', sa.Column('execution_id', sa.UUID(), nullable=True))
    op.add_column('agent_executions', sa.Column('agent_type', sa.String(length=100), nullable=True))
    op.add_column('agent_executions', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent_executions', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent_executions', sa.Column('duration', sa.Float(), nullable=True))
    op.add_column('agent_executions', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_executions', sa.Column('quality_score', sa.Float(), nullable=True))
    op.add_column('agent_executions', sa.Column('error', sa.Text(), nullable=True))
    op.add_column('agent_executions', sa.Column('metadata', sa.JSON(), nullable=True))

    # Add foreign key constraint for execution_id
    op.create_foreign_key(
        'fk_agent_executions_execution_id',
        'agent_executions', 'executions',
        ['execution_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_agent_executions_execution_id'), 'agent_executions', ['execution_id'], unique=False)

    # Note: We keep nullable=True for execution_id/agent_type to support existing records,
    # or drop agent_id/input_data/output_data columns
    try:
        op.drop_constraint('agent_executions_agent_id_fkey', 'agent_executions', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('agent_executions', 'agent_id')
        op.drop_column('agent_executions', 'input_data')
        op.drop_column('agent_executions', 'output_data')
    except Exception:
        pass

    # 3. EXECUTION_EVENTS TABLE
    op.create_table(
        'execution_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('agent_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_events_execution_id'), 'execution_events', ['execution_id'], unique=False)
    op.create_index(op.f('ix_execution_events_event_type'), 'execution_events', ['event_type'], unique=False)

    # 4. EXECUTION_CHECKPOINTS TABLE
    op.create_table(
        'execution_checkpoints',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('node_name', sa.String(length=100), nullable=False),
        sa.Column('state_snapshot', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_checkpoints_execution_id'), 'execution_checkpoints', ['execution_id'], unique=False)

    # 5. TOOL_EXECUTIONS TABLE
    op.create_table(
        'tool_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('tool_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('arguments_hash', sa.String(length=64), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_executions_execution_id'), 'tool_executions', ['execution_id'], unique=False)
    op.create_index(op.f('ix_tool_executions_tool_id'), 'tool_executions', ['tool_id'], unique=False)

def downgrade() -> None:
    # Drop tables
    op.drop_table('tool_executions')
    op.drop_table('execution_checkpoints')
    op.drop_table('execution_events')
    
    # Revert agent_executions alterations
    try:
        op.drop_constraint('fk_agent_executions_execution_id', 'agent_executions', type_='foreignkey')
    except Exception:
        pass
    op.drop_index(op.f('ix_agent_executions_execution_id'), 'agent_executions')
    
    try:
        op.drop_column('agent_executions', 'execution_id')
        op.drop_column('agent_executions', 'agent_type')
        op.drop_column('agent_executions', 'started_at')
        op.drop_column('agent_executions', 'completed_at')
        op.drop_column('agent_executions', 'duration')
        op.drop_column('agent_executions', 'retry_count')
        op.drop_column('agent_executions', 'quality_score')
        op.drop_column('agent_executions', 'error')
        op.drop_column('agent_executions', 'metadata')
    except Exception:
        pass

    op.drop_table('executions')
