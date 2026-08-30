"""knowledge graph migration

Revision ID: 008_knowledge_graph
Revises: 007_rag_queries
Create Date: 2026-08-29 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_knowledge_graph'
down_revision: Union[str, None] = '007_rag_queries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create knowledge_graph_nodes table
    op.create_table(
        'knowledge_graph_nodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    op.create_index('ix_knowledge_graph_nodes_user_id', 'knowledge_graph_nodes', ['user_id'])
    op.create_index('ix_knowledge_graph_nodes_workspace_id', 'knowledge_graph_nodes', ['workspace_id'])
    op.create_index('ix_knowledge_graph_nodes_node_type', 'knowledge_graph_nodes', ['node_type'])
    op.create_index('ix_knowledge_graph_nodes_external_id', 'knowledge_graph_nodes', ['external_id'])
    op.create_index('ix_kg_nodes_ws_type', 'knowledge_graph_nodes', ['workspace_id', 'node_type'])
    op.create_index('ix_kg_nodes_ws_ext', 'knowledge_graph_nodes', ['workspace_id', 'external_id'])
    op.create_index('ix_kg_nodes_user_ws', 'knowledge_graph_nodes', ['user_id', 'workspace_id'])

    # 2. Create knowledge_graph_edges table
    op.create_table(
        'knowledge_graph_edges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.UUID(), nullable=False),
        sa.Column('target_node_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_node_id'], ['knowledge_graph_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['knowledge_graph_nodes.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('source_node_id', 'target_node_id', 'relationship_type', name='uq_kg_edges_src_tgt_rel')
    )
    op.create_index('ix_knowledge_graph_edges_user_id', 'knowledge_graph_edges', ['user_id'])
    op.create_index('ix_knowledge_graph_edges_workspace_id', 'knowledge_graph_edges', ['workspace_id'])
    op.create_index('ix_knowledge_graph_edges_source_node_id', 'knowledge_graph_edges', ['source_node_id'])
    op.create_index('ix_knowledge_graph_edges_target_node_id', 'knowledge_graph_edges', ['target_node_id'])
    op.create_index('ix_knowledge_graph_edges_relationship_type', 'knowledge_graph_edges', ['relationship_type'])
    op.create_index('ix_kg_edges_ws_user', 'knowledge_graph_edges', ['workspace_id', 'user_id'])
    op.create_index('ix_kg_edges_src_type', 'knowledge_graph_edges', ['source_node_id', 'relationship_type'])
    op.create_index('ix_kg_edges_tgt_type', 'knowledge_graph_edges', ['target_node_id', 'relationship_type'])

def downgrade() -> None:
    # 1. Drop knowledge_graph_edges table and indexes
    op.drop_index('ix_kg_edges_tgt_type', table_name='knowledge_graph_edges')
    op.drop_index('ix_kg_edges_src_type', table_name='knowledge_graph_edges')
    op.drop_index('ix_kg_edges_ws_user', table_name='knowledge_graph_edges')
    op.drop_index('ix_knowledge_graph_edges_relationship_type', table_name='knowledge_graph_edges')
    op.drop_index('ix_knowledge_graph_edges_target_node_id', table_name='knowledge_graph_edges')
    op.drop_index('ix_knowledge_graph_edges_source_node_id', table_name='knowledge_graph_edges')
    op.drop_index('ix_knowledge_graph_edges_workspace_id', table_name='knowledge_graph_edges')
    op.drop_index('ix_knowledge_graph_edges_user_id', table_name='knowledge_graph_edges')
    op.drop_table('knowledge_graph_edges')

    # 2. Drop knowledge_graph_nodes table and indexes
    op.drop_index('ix_kg_nodes_user_ws', table_name='knowledge_graph_nodes')
    op.drop_index('ix_kg_nodes_ws_ext', table_name='knowledge_graph_nodes')
    op.drop_index('ix_kg_nodes_ws_type', table_name='knowledge_graph_nodes')
    op.drop_index('ix_knowledge_graph_nodes_external_id', table_name='knowledge_graph_nodes')
    op.drop_index('ix_knowledge_graph_nodes_node_type', table_name='knowledge_graph_nodes')
    op.drop_index('ix_knowledge_graph_nodes_workspace_id', table_name='knowledge_graph_nodes')
    op.drop_index('ix_knowledge_graph_nodes_user_id', table_name='knowledge_graph_nodes')
    op.drop_table('knowledge_graph_nodes')
