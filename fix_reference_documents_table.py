#!/usr/bin/env python3
"""
Script to fix the reference_documents table by adding the missing source_pending_document_id column.
This addresses the error: 'column "source_pending_document_id" of relation "reference_documents" does not exist'
"""

import sys
from sqlalchemy import create_engine, text
from app.config.settings import get_settings

def fix_reference_documents_table():
    """Add the missing source_pending_document_id column to the reference_documents table."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check if the column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'reference_documents' 
            AND column_name = 'source_pending_document_id'
        """)).fetchone()
        
        if result:
            print("Column 'source_pending_document_id' already exists in reference_documents table.")
            return
        
        # Add the missing column
        try:
            conn.execute(text("""
                ALTER TABLE reference_documents 
                ADD COLUMN source_pending_document_id INTEGER
            """))
            
            # Add foreign key constraint
            conn.execute(text("""
                ALTER TABLE reference_documents 
                ADD CONSTRAINT fk_reference_documents_pending_document 
                FOREIGN KEY (source_pending_document_id) 
                REFERENCES pending_reference_documents (id)
            """))
            
            conn.commit()
            print("Successfully added 'source_pending_document_id' column to reference_documents table.")
        except Exception as e:
            conn.rollback()
            print(f"Error adding column: {e}")
            raise

if __name__ == "__main__":
    try:
        fix_reference_documents_table()
        print("Reference documents table fixed successfully!")
    except Exception as e:
        print(f"Error fixing reference_documents table: {e}")
        sys.exit(1)
