"""add_word_pair_counters

Revision ID: 810ef7b8d7fc
Revises: 001
Create Date: 2025-05-10 12:53:03.311365

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '810ef7b8d7fc'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create word_pair_counters table
    op.create_table(
        'word_pair_counters',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('word1', sa.String(255), nullable=False, index=True),  # The word that is beaten
        sa.Column('word2', sa.String(255), nullable=False, index=True),  # The word that beats
        sa.Column('count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )
    
    # Create composite index for fast lookups
    op.create_index(
        'ix_word_pair_counters_word1_word2',
        'word_pair_counters',
        ['word1', 'word2'],
        unique=True
    )


def downgrade() -> None:
    op.drop_index('ix_word_pair_counters_word1_word2', table_name='word_pair_counters')
    op.drop_table('word_pair_counters')