#!/usr/bin/env python3
"""
Script to drop and recreate the reference_documents table using direct SQL commands.
"""

import sys
from sqlalchemy import create_engine, text
from app.config.settings import get_settings

def recreate_reference_table():
    """Drop and recreate the reference_documents table using direct SQL."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Begin transaction
        trans = conn.begin()
        try:
            # Check if the table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'reference_documents'
                )
            """)).fetchone()
            
            table_exists = result[0] if result else False
            
            if table_exists:
                print("Dropping existing reference_documents table...")
                
                # First check for foreign keys referencing this table
                fk_references = conn.execute(text("""
                    SELECT tc.table_name, tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                    WHERE ccu.table_name = 'reference_documents' AND tc.constraint_type = 'FOREIGN KEY'
                """)).fetchall()
                
                # Drop those foreign keys
                for table_name, constraint_name in fk_references:
                    print(f"Dropping foreign key {constraint_name} from table {table_name}")
                    conn.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"))
                
                # Drop the table
                conn.execute(text("DROP TABLE IF EXISTS reference_documents CASCADE"))
                print("Table dropped successfully.")
            
            # Create the table with the correct structure
            print("Creating reference_documents table...")
            conn.execute(text("""
                CREATE TABLE reference_documents (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    object_id VARCHAR(255) UNIQUE NOT NULL,
                    content_type VARCHAR(100),
                    document_metadata JSONB,
                    created_by INTEGER REFERENCES users(id),
                    source_pending_document_id INTEGER,
                    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
                )
            """))
            
            # Create index
            conn.execute(text("CREATE INDEX ix_reference_documents_id ON reference_documents (id)"))
            
            # Add foreign key constraint to pending_reference_documents if that table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pending_reference_documents'
                )
            """)).fetchone()
            
            if result and result[0]:
                conn.execute(text("""
                    ALTER TABLE reference_documents 
                    ADD CONSTRAINT fk_reference_documents_pending_document 
                    FOREIGN KEY (source_pending_document_id) 
                    REFERENCES pending_reference_documents (id)
                """))
            
            # Commit the transaction
            trans.commit()
            
            # Verify the table structure
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'reference_documents'
                ORDER BY ordinal_position
            """)).fetchall()
            
            print("\nNew table structure:")
            for column in result:
                print(f"  - {column[0]}: {column[1]}")
                
        except Exception as e:
            trans.rollback()
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    try:
        recreate_reference_table()
        print("\nReference documents table recreated successfully!")
    except Exception as e:
        print(f"Error recreating reference_documents table: {e}")
        sys.exit(1)
