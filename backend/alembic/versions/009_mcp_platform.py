"""mcp platform foundation

Revision ID: 009_mcp_platform
Revises: 008_knowledge_graph
Create Date: 2026-08-31 08:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_mcp_platform'
down_revision = '008_knowledge_graph'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Clean up old placeholder tables if they exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'mcp_connections' in tables:
        op.drop_table('mcp_connections')
    if 'mcp_tools' in tables:
        op.drop_table('mcp_tools')
    if 'mcp_servers' in tables:
        op.drop_table('mcp_servers')

    # 2. Create production mcp_servers table
    op.create_table(
        'mcp_servers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('server_url', sa.String(length=512), nullable=False),
        sa.Column('transport', sa.String(length=50), nullable=False, server_default='sse'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='inactive'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('authentication_type', sa.String(length=50), nullable=False, server_default='none'),
        sa.Column('auth_config', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('last_connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_mcp_servers_workspace_name')
    )
    op.create_index(op.f('ix_mcp_servers_user_id'), 'mcp_servers', ['user_id'], unique=False)
    op.create_index(op.f('ix_mcp_servers_workspace_id'), 'mcp_servers', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_mcp_servers_name'), 'mcp_servers', ['name'], unique=False)

    # 3. Create production mcp_capabilities table
    op.create_table(
        'mcp_capabilities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('server_id', sa.UUID(), nullable=False),
        sa.Column('capability_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('input_schema', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['server_id'], ['mcp_servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('server_id', 'capability_type', 'name', name='uq_mcp_capability_server_type_name')
    )
    op.create_index(op.f('ix_mcp_capabilities_server_id'), 'mcp_capabilities', ['server_id'], unique=False)
    op.create_index(op.f('ix_mcp_capabilities_capability_type'), 'mcp_capabilities', ['capability_type'], unique=False)
    op.create_index(op.f('ix_mcp_capabilities_name'), 'mcp_capabilities', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mcp_capabilities_name'), table_name='mcp_capabilities')
    op.drop_index(op.f('ix_mcp_capabilities_capability_type'), table_name='mcp_capabilities')
    op.drop_index(op.f('ix_mcp_capabilities_server_id'), table_name='mcp_capabilities')
    op.drop_table('mcp_capabilities')

    op.drop_index(op.f('ix_mcp_servers_name'), table_name='mcp_servers')
    op.drop_index(op.f('ix_mcp_servers_workspace_id'), table_name='mcp_servers')
    op.drop_index(op.f('ix_mcp_servers_user_id'), table_name='mcp_servers')
    op.drop_table('mcp_servers')
