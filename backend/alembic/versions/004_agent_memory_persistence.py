"""agent memory persistence

Revision ID: 004_agent_memory_persistence
Revises: 003_execution_persistence
Create Date: 2026-08-12 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType

revision: str = '004_agent_memory_persistence'
down_revision: Union[str, None] = '003_execution_persistence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

class AlembicVector(UserDefinedType):
    def get_col_spec(self, **kw):
        return "vector(1536)"

def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Create vector extension if not exists
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.create_table(
            'agent_memories',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.UUID(), nullable=True),
            sa.Column('updated_by', sa.UUID(), nullable=True),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('workspace_id', sa.UUID(), nullable=False),
            sa.Column('memory_type', sa.String(length=50), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('source', sa.String(length=100), nullable=False),
            sa.Column('importance', sa.Float(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('embedding', AlembicVector(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
        )
    else:
        op.create_table(
            'agent_memories',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.UUID(), nullable=True),
            sa.Column('updated_by', sa.UUID(), nullable=True),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('workspace_id', sa.UUID(), nullable=False),
            sa.Column('memory_type', sa.String(length=50), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('source', sa.String(length=100), nullable=False),
            sa.Column('importance', sa.Float(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('embedding', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
        )

def downgrade() -> None:
    op.drop_table('agent_memories')
