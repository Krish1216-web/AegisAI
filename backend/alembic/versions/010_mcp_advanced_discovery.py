"""mcp advanced discovery

Revision ID: 010_mcp_advanced_discovery
Revises: 009_mcp_platform
Create Date: 2026-08-31 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_mcp_advanced_discovery'
down_revision = '009_mcp_platform'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add fields to mcp_servers
    op.add_column('mcp_servers', sa.Column('server_version', sa.String(length=50), nullable=True))
    op.add_column('mcp_servers', sa.Column('protocol_version', sa.String(length=50), nullable=True, server_default='2024-11-05'))
    op.add_column('mcp_servers', sa.Column('last_health_check_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('mcp_servers', sa.Column('last_discovery_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('mcp_servers', sa.Column('last_error', sa.Text(), nullable=True))
    op.create_index(op.f('ix_mcp_servers_server_url'), 'mcp_servers', ['server_url'], unique=False)

    # 2. Add fields to mcp_capabilities
    op.add_column('mcp_capabilities', sa.Column('definition_hash', sa.String(length=64), nullable=True))
    op.add_column('mcp_capabilities', sa.Column('is_stale', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('mcp_capabilities', sa.Column('stale_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('mcp_capabilities', sa.Column('first_discovered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('mcp_capabilities', sa.Column('last_discovered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('mcp_capabilities', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.create_index(op.f('ix_mcp_capabilities_definition_hash'), 'mcp_capabilities', ['definition_hash'], unique=False)
    op.create_index(op.f('ix_mcp_capabilities_is_stale'), 'mcp_capabilities', ['is_stale'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mcp_capabilities_is_stale'), table_name='mcp_capabilities')
    op.drop_index(op.f('ix_mcp_capabilities_definition_hash'), table_name='mcp_capabilities')
    op.drop_column('mcp_capabilities', 'version')
    op.drop_column('mcp_capabilities', 'last_discovered_at')
    op.drop_column('mcp_capabilities', 'first_discovered_at')
    op.drop_column('mcp_capabilities', 'stale_at')
    op.drop_column('mcp_capabilities', 'is_stale')
    op.drop_column('mcp_capabilities', 'definition_hash')

    op.drop_index(op.f('ix_mcp_servers_server_url'), table_name='mcp_servers')
    op.drop_column('mcp_servers', 'last_error')
    op.drop_column('mcp_servers', 'last_discovery_at')
    op.drop_column('mcp_servers', 'last_health_check_at')
    op.drop_column('mcp_servers', 'protocol_version')
    op.drop_column('mcp_servers', 'server_version')
