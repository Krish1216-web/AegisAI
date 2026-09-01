"""shared_projects_resources

Revision ID: 016_shared_projects_resources
Revises: 015_team_invitations
Create Date: 2026-09-01 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = '016_shared_projects_resources'
down_revision = '015_team_invitations'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('created_by', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_workspace_project_name')
    )
    op.create_index('ix_projects_workspace_id', 'projects', ['workspace_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])

    op.create_table(
        'project_memberships',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), default='viewer', nullable=False),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_user_membership')
    )
    op.create_index('ix_project_memberships_project_id', 'project_memberships', ['project_id'])
    op.create_index('ix_project_memberships_user_id', 'project_memberships', ['user_id'])
    op.create_index('ix_project_memberships_status', 'project_memberships', ['status'])

    op.create_table(
        'project_resources',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('created_by', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'resource_type', 'resource_id', name='uq_project_resource_link')
    )
    op.create_index('ix_project_resources_project_id', 'project_resources', ['project_id'])
    op.create_index('ix_project_resources_workspace_id', 'project_resources', ['workspace_id'])
    op.create_index('ix_project_resources_resource_type', 'project_resources', ['resource_type'])
    op.create_index('ix_project_resources_resource_id', 'project_resources', ['resource_id'])

def downgrade():
    op.drop_table('project_resources')
    op.drop_table('project_memberships')
    op.drop_table('projects')
