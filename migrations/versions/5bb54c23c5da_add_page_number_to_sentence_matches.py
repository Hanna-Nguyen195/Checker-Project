"""add_page_number_to_sentence_matches

Revision ID: 5bb54c23c5da
Revises: 129387c99828
Create Date: 2025-09-25 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bb54c23c5da'
down_revision = '129387c99828'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First check if the table exists before trying to modify it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'sentence_matches' in inspector.get_table_names():
        # Check if the column already exists
        columns = [col['name'] for col in inspector.get_columns('sentence_matches')]
        if 'page_number' not in columns:
            op.add_column('sentence_matches', sa.Column('page_number', sa.Integer(), nullable=True, server_default='1'))
    else:
        # Create the sentence_matches table if it doesn't exist
        op.create_table(
            'sentence_matches',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('match_id', sa.Integer(), nullable=False),
            sa.Column('user_sentence_text', sa.String(), nullable=False),
            sa.Column('user_sentence_start', sa.Integer(), nullable=False),
            sa.Column('user_sentence_end', sa.Integer(), nullable=False),
            sa.Column('reference_sentence_text', sa.String(), nullable=False),
            sa.Column('reference_sentence_start', sa.Integer(), nullable=False),
            sa.Column('reference_sentence_end', sa.Integer(), nullable=False),
            sa.Column('similarity_score', sa.Float(), nullable=False),
            sa.Column('match_type', sa.String(20), default="exact", nullable=False),
            sa.Column('page_number', sa.Integer(), nullable=True, server_default='1'),
            sa.Column('bounding_boxes', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['match_id'], ['plagiarism_matches.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_match_sentences', 'sentence_matches', ['match_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'sentence_matches' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('sentence_matches')]
        if 'page_number' in columns:
            op.drop_column('sentence_matches', 'page_number')
