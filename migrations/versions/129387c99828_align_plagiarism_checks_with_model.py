"""align_plagiarism_checks_with_model

Revision ID: 129387c99828
Revises: 5bb54c23c5da
Create Date: 2025-09-24 18:41:02.792074

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '129387c99828'
down_revision = '892cab847da0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Make plagiarism_document_id NOT NULL
    # First, ensure all records have a valid plagiarism_document_id
    op.execute('''
        UPDATE plagiarism_checks 
        SET plagiarism_document_id = check_document_id 
        WHERE plagiarism_document_id IS NULL
    ''')
    
    # Then alter the column to be NOT NULL
    op.alter_column('plagiarism_checks', 'plagiarism_document_id',
               existing_type=sa.Integer(),
               nullable=False)
    
    # Step 2: Drop the foreign key constraint for check_document_id
    op.drop_constraint('fk_plagiarism_checks_check_document_id', 'plagiarism_checks', type_='foreignkey')
    
    # Step 3: Drop the check_document_id column
    op.drop_column('plagiarism_checks', 'check_document_id')


def downgrade() -> None:
    # Step 1: Add back the check_document_id column
    op.add_column('plagiarism_checks',
                  sa.Column('check_document_id', sa.Integer(), nullable=True))
    
    # Step 2: Copy data from plagiarism_document_id to check_document_id
    op.execute('''
        UPDATE plagiarism_checks 
        SET check_document_id = plagiarism_document_id
    ''')
    
    # Step 3: Make check_document_id NOT NULL
    op.alter_column('plagiarism_checks', 'check_document_id',
               existing_type=sa.Integer(),
               nullable=False)
    
    # Step 4: Add back the foreign key constraint
    op.create_foreign_key('fk_plagiarism_checks_check_document_id',
                      'plagiarism_checks', 'check_documents',
                      ['check_document_id'], ['id'])
    
    # Step 5: Allow plagiarism_document_id to be NULL again
    op.alter_column('plagiarism_checks', 'plagiarism_document_id',
               existing_type=sa.Integer(),
               nullable=True)
