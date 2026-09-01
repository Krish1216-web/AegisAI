"""team_invitations

Revision ID: 015_team_invitations
Revises: 014_team_collaboration_foundation
Create Date: 2026-09-01 20:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '015_team_invitations'
down_revision: Union[str, None] = '014_team_collaboration_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'team_invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('invited_user_id', sa.UUID(), nullable=True),
        sa.Column('invited_email', sa.String(length=255), nullable=True),
        sa.Column('invited_by', sa.UUID(), nullable=True),
        sa.Column('token_hash', sa.String(length=64), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='member', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_invitations_team_id', 'team_invitations', ['team_id'], unique=False)
    op.create_index('ix_team_invitations_workspace_id', 'team_invitations', ['workspace_id'], unique=False)
    op.create_index('ix_team_invitations_invited_user_id', 'team_invitations', ['invited_user_id'], unique=False)
    op.create_index('ix_team_invitations_invited_email', 'team_invitations', ['invited_email'], unique=False)
    op.create_index('ix_team_invitations_token_hash', 'team_invitations', ['token_hash'], unique=False)
    op.create_index('ix_team_invitations_status', 'team_invitations', ['status'], unique=False)
    op.create_index('ix_team_invitations_expires_at', 'team_invitations', ['expires_at'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_team_invitations_expires_at', table_name='team_invitations')
    op.drop_index('ix_team_invitations_status', table_name='team_invitations')
    op.drop_index('ix_team_invitations_token_hash', table_name='team_invitations')
    op.drop_index('ix_team_invitations_invited_email', table_name='team_invitations')
    op.drop_index('ix_team_invitations_invited_user_id', table_name='team_invitations')
    op.drop_index('ix_team_invitations_workspace_id', table_name='team_invitations')
    op.drop_index('ix_team_invitations_team_id', table_name='team_invitations')
    op.drop_table('team_invitations')
