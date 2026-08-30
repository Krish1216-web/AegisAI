"""document chunks upgrade

Revision ID: 006_document_chunks
Revises: 005_documents
Create Date: 2026-08-18 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType

revision: str = '006_document_chunks'
down_revision: Union[str, None] = '005_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

class AlembicVector(UserDefinedType):
    def get_col_spec(self, **kw):
        return "vector(1536)"

def upgrade() -> None:
    # 1. Drop existing placeholder document_chunks table
    op.drop_table('document_chunks')

    # 2. Determine dialect database and select vector type column
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    embedding_col = AlembicVector() if is_postgres else sa.JSON()

    # 3. Create upgraded document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('character_count', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.String(length=255), nullable=True),
        sa.Column('start_offset', sa.Integer(), nullable=True),
        sa.Column('end_offset', sa.Integer(), nullable=True),
        sa.Column('embedding', embedding_col, nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('embedding_dimension', sa.Integer(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunks_doc_chunk')
    )

    # 4. Create indices
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])
    op.create_index('ix_document_chunks_user_id', 'document_chunks', ['user_id'])
    op.create_index('ix_document_chunks_workspace_id', 'document_chunks', ['workspace_id'])
    op.create_index('ix_document_chunks_content_hash', 'document_chunks', ['content_hash'])
    op.create_index('ix_document_chunks_chunk_index', 'document_chunks', ['chunk_index'])

def downgrade() -> None:
    # 1. Drop indices
    op.drop_index('ix_document_chunks_chunk_index', table_name='document_chunks')
    op.drop_index('ix_document_chunks_content_hash', table_name='document_chunks')
    op.drop_index('ix_document_chunks_workspace_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_user_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')

    # 2. Drop upgraded table
    op.drop_table('document_chunks')

    # 3. Recreate original document_chunks placeholder table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE')
    )
