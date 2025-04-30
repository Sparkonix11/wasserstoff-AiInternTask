"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-04-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create word_counters table
    op.create_table(
        'word_counters',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('word', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )
    
    # Create verdict_cache table
    op.create_table(
        'verdict_cache',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('word1', sa.String(255), nullable=False),
        sa.Column('word2', sa.String(255), nullable=False),
        sa.Column('verdict', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create composite index for faster lookups
    op.create_index(
        'ix_verdict_cache_word1_word2',
        'verdict_cache',
        ['word1', 'word2'],
        unique=True
    )
    
    # Create game_sessions table
    op.create_table(
        'game_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('current_word', sa.String(255), nullable=False),
        sa.Column('score', sa.Integer(), default=0),
        sa.Column('game_over', sa.Boolean(), default=False),
        sa.Column('persona', sa.String(50), default="default"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('history', sa.Text(), nullable=False)
    )
    
    # Create game_statistics table
    op.create_table(
        'game_statistics',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('total_games', sa.Integer(), default=0),
        sa.Column('total_guesses', sa.Integer(), default=0),
        sa.Column('avg_score', sa.Float(), default=0.0),
        sa.Column('max_score', sa.Integer(), default=0),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )

    # Insert initial statistics record
    op.execute(
        "INSERT INTO game_statistics (id, total_games, total_guesses, avg_score, max_score) VALUES (1, 0, 0, 0.0, 0)"
    )


def downgrade() -> None:
    op.drop_table('game_statistics')
    op.drop_table('game_sessions')
    op.drop_index('ix_verdict_cache_word1_word2', table_name='verdict_cache')
    op.drop_table('verdict_cache')
    op.drop_table('word_counters')