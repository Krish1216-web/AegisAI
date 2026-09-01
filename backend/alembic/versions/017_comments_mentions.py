"""comments_mentions

Revision ID: 017_comments_mentions
Revises: 016_shared_projects_resources
Create Date: 2026-09-01 21:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = '017_comments_mentions'
down_revision = '016_shared_projects_resources'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'comments',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('parent_comment_id', sa.UUID(), sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_comments_workspace_id', 'comments', ['workspace_id'])
    op.create_index('ix_comments_author_id', 'comments', ['author_id'])
    op.create_index('ix_comments_project_id', 'comments', ['project_id'])
    op.create_index('ix_comments_resource_type', 'comments', ['resource_type'])
    op.create_index('ix_comments_resource_id', 'comments', ['resource_id'])
    op.create_index('ix_comments_parent_comment_id', 'comments', ['parent_comment_id'])
    op.create_index('ix_comments_status', 'comments', ['status'])

    op.create_table(
        'comment_mentions',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('comment_id', sa.UUID(), sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mentioned_user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('comment_id', 'mentioned_user_id', name='uq_comment_user_mention')
    )
    op.create_index('ix_comment_mentions_comment_id', 'comment_mentions', ['comment_id'])
    op.create_index('ix_comment_mentions_mentioned_user_id', 'comment_mentions', ['mentioned_user_id'])

def downgrade():
    op.drop_table('comment_mentions')
    op.drop_table('comments')
