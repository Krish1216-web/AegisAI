"""workflow approval governance

Revision ID: 012_workflow_approval_governance
Revises: 011_workflow_engine_foundation
Create Date: 2026-08-31 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012_workflow_approval_governance'
down_revision = '011_workflow_engine_foundation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_approval_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('workflow_node_id', sa.UUID(), nullable=True),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('node_key', sa.String(length=100), nullable=False),
        sa.Column('requested_by', sa.UUID(), nullable=False),
        sa.Column('assigned_roles', sa.JSON(), nullable=False),
        sa.Column('assigned_users', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('policy', sa.String(length=50), nullable=False, server_default='single_approver'),
        sa.Column('required_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('requester_can_approve', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('title', sa.String(length=200), nullable=False, server_default='Approval Request'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='86400'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('decision_history', sa.JSON(), nullable=False),
        sa.Column('metadata_payload', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_node_id'], ['workflow_nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_approval_requests_execution_id'), 'workflow_approval_requests', ['execution_id'], unique=False)
    op.create_index(op.f('ix_workflow_approval_requests_workflow_id'), 'workflow_approval_requests', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_workflow_approval_requests_workspace_id'), 'workflow_approval_requests', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_workflow_approval_requests_node_key'), 'workflow_approval_requests', ['node_key'], unique=False)
    op.create_index(op.f('ix_workflow_approval_requests_requested_by'), 'workflow_approval_requests', ['requested_by'], unique=False)
    op.create_index(op.f('ix_workflow_approval_requests_status'), 'workflow_approval_requests', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_approval_requests_status'), table_name='workflow_approval_requests')
    op.drop_index(op.f('ix_workflow_approval_requests_requested_by'), table_name='workflow_approval_requests')
    op.drop_index(op.f('ix_workflow_approval_requests_node_key'), table_name='workflow_approval_requests')
    op.drop_index(op.f('ix_workflow_approval_requests_workspace_id'), table_name='workflow_approval_requests')
    op.drop_index(op.f('ix_workflow_approval_requests_workflow_id'), table_name='workflow_approval_requests')
    op.drop_index(op.f('ix_workflow_approval_requests_execution_id'), table_name='workflow_approval_requests')
    op.drop_table('workflow_approval_requests')
