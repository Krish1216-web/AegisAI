"""user avatar and audit schema synchronization

Revision ID: 020_user_avatar_schema_sync
Revises: 019_background_jobs
Create Date: 2026-10-09 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '020_user_avatar_schema_sync'
down_revision: Union[str, None] = '019_background_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_existing_columns(inspector, table_name: str) -> set:
    tables = inspector.get_table_names()
    if table_name not in tables:
        return set()
    return {c['name'] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. users: avatar_url, settings
    if 'users' in existing_tables:
        user_cols = _get_existing_columns(inspector, 'users')
        if 'avatar_url' not in user_cols:
            op.add_column('users', sa.Column('avatar_url', sa.String(length=512), nullable=True))
        if 'settings' not in user_cols:
            op.add_column('users', sa.Column('settings', sa.JSON(), nullable=True))

    # 2. teams: deleted_at, updated_by
    if 'teams' in existing_tables:
        team_cols = _get_existing_columns(inspector, 'teams')
        if 'deleted_at' not in team_cols:
            op.add_column('teams', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'updated_by' not in team_cols:
            op.add_column('teams', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 3. team_memberships: deleted_at, created_by, updated_by
    if 'team_memberships' in existing_tables:
        tm_cols = _get_existing_columns(inspector, 'team_memberships')
        if 'deleted_at' not in tm_cols:
            op.add_column('team_memberships', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'created_by' not in tm_cols:
            op.add_column('team_memberships', sa.Column('created_by', sa.UUID(), nullable=True))
        if 'updated_by' not in tm_cols:
            op.add_column('team_memberships', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 4. team_invitations: deleted_at, created_by, updated_by
    if 'team_invitations' in existing_tables:
        ti_cols = _get_existing_columns(inspector, 'team_invitations')
        if 'deleted_at' not in ti_cols:
            op.add_column('team_invitations', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'created_by' not in ti_cols:
            op.add_column('team_invitations', sa.Column('created_by', sa.UUID(), nullable=True))
        if 'updated_by' not in ti_cols:
            op.add_column('team_invitations', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 5. projects: deleted_at, updated_by
    if 'projects' in existing_tables:
        proj_cols = _get_existing_columns(inspector, 'projects')
        if 'deleted_at' not in proj_cols:
            op.add_column('projects', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'updated_by' not in proj_cols:
            op.add_column('projects', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 6. project_memberships: deleted_at, created_by, updated_by
    if 'project_memberships' in existing_tables:
        pm_cols = _get_existing_columns(inspector, 'project_memberships')
        if 'deleted_at' not in pm_cols:
            op.add_column('project_memberships', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'created_by' not in pm_cols:
            op.add_column('project_memberships', sa.Column('created_by', sa.UUID(), nullable=True))
        if 'updated_by' not in pm_cols:
            op.add_column('project_memberships', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 7. project_resources: deleted_at, updated_by
    if 'project_resources' in existing_tables:
        pr_cols = _get_existing_columns(inspector, 'project_resources')
        if 'deleted_at' not in pr_cols:
            op.add_column('project_resources', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'updated_by' not in pr_cols:
            op.add_column('project_resources', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 8. comments: created_by, updated_by
    if 'comments' in existing_tables:
        c_cols = _get_existing_columns(inspector, 'comments')
        if 'created_by' not in c_cols:
            op.add_column('comments', sa.Column('created_by', sa.UUID(), nullable=True))
        if 'updated_by' not in c_cols:
            op.add_column('comments', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 9. notifications: deleted_at, created_by, updated_by
    if 'notifications' in existing_tables:
        n_cols = _get_existing_columns(inspector, 'notifications')
        if 'deleted_at' not in n_cols:
            op.add_column('notifications', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'created_by' not in n_cols:
            op.add_column('notifications', sa.Column('created_by', sa.UUID(), nullable=True))
        if 'updated_by' not in n_cols:
            op.add_column('notifications', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 10. notification_preferences: deleted_at, created_by, updated_by
    if 'notification_preferences' in existing_tables:
        np_cols = _get_existing_columns(inspector, 'notification_preferences')
        if 'deleted_at' not in np_cols:
            op.add_column('notification_preferences', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        if 'created_by' not in np_cols:
            op.add_column('notification_preferences', sa.Column('created_by', sa.UUID(), nullable=True))
        if 'updated_by' not in np_cols:
            op.add_column('notification_preferences', sa.Column('updated_by', sa.UUID(), nullable=True))

    # 11. background_jobs: updated_by
    if 'background_jobs' in existing_tables:
        bj_cols = _get_existing_columns(inspector, 'background_jobs')
        if 'updated_by' not in bj_cols:
            op.add_column('background_jobs', sa.Column('updated_by', sa.UUID(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for tbl, cols in [
        ('background_jobs', ['updated_by']),
        ('notification_preferences', ['updated_by', 'created_by', 'deleted_at']),
        ('notifications', ['updated_by', 'created_by', 'deleted_at']),
        ('comments', ['updated_by', 'created_by']),
        ('project_resources', ['updated_by', 'deleted_at']),
        ('project_memberships', ['updated_by', 'created_by', 'deleted_at']),
        ('projects', ['updated_by', 'deleted_at']),
        ('team_invitations', ['updated_by', 'created_by', 'deleted_at']),
        ('team_memberships', ['updated_by', 'created_by', 'deleted_at']),
        ('teams', ['updated_by', 'deleted_at']),
        ('users', ['settings', 'avatar_url']),
    ]:
        existing = _get_existing_columns(inspector, tbl)
        for col in cols:
            if col in existing:
                op.drop_column(tbl, col)
