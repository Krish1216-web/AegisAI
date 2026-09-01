"""notifications_realtime

Revision ID: 018_notifications_realtime
Revises: 017_comments_mentions
Create Date: 2026-09-01 21:42:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = '018_notifications_realtime'
down_revision = '017_comments_mentions'
branch_labels = None
depends_on = None

def upgrade():
    # We alter or recreate the notifications table to match the robust collaboration schema
    # In SQLite / PostgreSQL alembic safe migrations:
    try:
        op.drop_table('notification_preferences')
        op.drop_table('notifications')
    except Exception:
        pass

    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('team_id', sa.UUID(), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=True),
        sa.Column('comment_id', sa.UUID(), sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('mention_id', sa.UUID(), sa.ForeignKey('comment_mentions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('status', sa.String(20), default='unread', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_notifications_workspace_id', 'notifications', ['workspace_id'])
    op.create_index('ix_notifications_recipient_user_id', 'notifications', ['recipient_user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_status', 'notifications', ['status'])

    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.UUID(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('notification_type', sa.String(50), default='all', nullable=False),
        sa.Column('in_app_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('email_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('push_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'workspace_id', 'notification_type', name='uq_user_ws_notif_type')
    )
    op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'])

def downgrade():
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
