"""team_collaboration_foundation

Revision ID: 014_team_collaboration_foundation
Revises: 013_workflow_scheduling
Create Date: 2026-09-01 12:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '014_team_collaboration_foundation'
down_revision: Union[str, None] = '013_workflow_scheduling'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_team_workspace_name')
    )
    op.create_index('ix_teams_workspace_id', 'teams', ['workspace_id'], unique=False)

    # 2. Create team_memberships table
    op.create_table(
        'team_memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='member', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_membership_user')
    )
    op.create_index('ix_team_memberships_team_id', 'team_memberships', ['team_id'], unique=False)
    op.create_index('ix_team_memberships_user_id', 'team_memberships', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_team_memberships_user_id', table_name='team_memberships')
    op.drop_index('ix_team_memberships_team_id', table_name='team_memberships')
    op.drop_table('team_memberships')
    op.drop_index('ix_teams_workspace_id', table_name='teams')
    op.drop_table('teams')
