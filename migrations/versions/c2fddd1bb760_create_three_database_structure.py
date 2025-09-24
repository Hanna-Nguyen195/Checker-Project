"""create_three_database_structure

Revision ID: c2fddd1bb760
Revises: 11c6713d0de7
Create Date: 2025-09-24 16:52:45.565005

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2fddd1bb760'
down_revision = '11c6713d0de7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new tables
    op.create_table(
        'plagiarism_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('object_id', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('document_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plagiarism_documents_id'), 'plagiarism_documents', ['id'], unique=False)
    
    op.create_table(
        'pending_reference_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('object_id', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('admin_comment', sa.String(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('document_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('object_id')
    )
    op.create_index(op.f('ix_pending_reference_documents_id'), 'pending_reference_documents', ['id'], unique=False)
    
    # Add new column to reference_documents
    op.add_column('reference_documents', 
                  sa.Column('source_pending_document_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_reference_documents_pending_document',
        'reference_documents', 'pending_reference_documents',
        ['source_pending_document_id'], ['id']
    )
    
    # Add new column to plagiarism_checks
    op.add_column('plagiarism_checks', 
                  sa.Column('plagiarism_document_id', sa.Integer(), nullable=True))
    
    # Migrate data from user_documents to the new tables
    # This requires a connection to execute SQL
    connection = op.get_bind()
    
    # Step 1: Migrate user documents used for plagiarism checking to plagiarism_documents
    connection.execute(
        """
        INSERT INTO plagiarism_documents (id, user_id, title, object_id, content_type, document_metadata, created_at, updated_at)
        SELECT id, user_id, title, object_id, content_type, NULL, created_at, updated_at
        FROM user_documents
        WHERE status NOT IN ('pending', 'rejected')
        """
    )
    
    # Step 2: Migrate pending reference documents to pending_reference_documents
    connection.execute(
        """
        INSERT INTO pending_reference_documents 
        (id, user_id, title, object_id, content_type, status, admin_comment, approved_by, approved_at, document_metadata, created_at, updated_at)
        SELECT id, user_id, COALESCE(title, 'Untitled'), object_id, content_type, status, comment, approved_by, approved_at, NULL, created_at, updated_at
        FROM user_documents
        WHERE status IN ('pending', 'rejected')
        """
    )
    
    # Step 3: Update plagiarism_checks to reference plagiarism_documents
    connection.execute(
        """
        UPDATE plagiarism_checks
        SET plagiarism_document_id = user_document_id
        """
    )
    
    # Make plagiarism_document_id non-nullable and add foreign key
    op.create_foreign_key(
        'fk_plagiarism_checks_document',
        'plagiarism_checks', 'plagiarism_documents',
        ['plagiarism_document_id'], ['id']
    )
    
    # Note: We're keeping user_document_id for now to ensure backward compatibility
    # It will be removed in a future migration after all code is updated


def downgrade() -> None:
    # Drop foreign key constraints first
    op.drop_constraint('fk_plagiarism_checks_document', 'plagiarism_checks', type_='foreignkey')
    op.drop_constraint('fk_reference_documents_pending_document', 'reference_documents', type_='foreignkey')
    
    # Drop new columns
    op.drop_column('plagiarism_checks', 'plagiarism_document_id')
    op.drop_column('reference_documents', 'source_pending_document_id')
    
    # Drop indexes
    op.drop_index(op.f('ix_pending_reference_documents_id'), table_name='pending_reference_documents')
    op.drop_index(op.f('ix_plagiarism_documents_id'), table_name='plagiarism_documents')
    
    # Drop new tables
    op.drop_table('pending_reference_documents')
    op.drop_table('plagiarism_documents')
