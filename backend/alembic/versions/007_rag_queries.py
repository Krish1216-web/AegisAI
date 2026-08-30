"""rag queries migration

Revision ID: 007_rag_queries
Revises: 006_document_chunks
Create Date: 2026-08-18 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_rag_queries'
down_revision: Union[str, None] = '006_document_chunks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'rag_queries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('citations', sa.JSON(), nullable=True),
        sa.Column('retrieved_chunks', sa.JSON(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('llm_provider', sa.String(length=50), nullable=False),
        sa.Column('llm_model', sa.String(length=100), nullable=False),
        sa.Column('is_cached', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    op.create_index('ix_rag_queries_user_id', 'rag_queries', ['user_id'])
    op.create_index('ix_rag_queries_workspace_id', 'rag_queries', ['workspace_id'])
    op.create_index('ix_rag_queries_created_at', 'rag_queries', ['created_at'])

def downgrade() -> None:
    op.drop_index('ix_rag_queries_created_at', table_name='rag_queries')
    op.drop_index('ix_rag_queries_workspace_id', table_name='rag_queries')
    op.drop_index('ix_rag_queries_user_id', table_name='rag_queries')
    op.drop_table('rag_queries')
