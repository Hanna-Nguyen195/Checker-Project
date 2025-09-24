#!/usr/bin/env python3
"""
Script to drop and recreate the reference_documents table according to the model definition.
This will resolve any schema mismatches between the database and the code model.
"""

import sys
from sqlalchemy import create_engine, text
from app.config.settings import get_settings
from app.models.document import ReferenceDocument
from app.config.database import Base

def recreate_reference_documents_table():
    """Drop and recreate the reference_documents table."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
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
            # First identify tables that reference reference_documents
            print("Identifying tables with foreign keys to reference_documents...")
            fk_tables = conn.execute(text("""
                SELECT tc.table_name, tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE ccu.table_name = 'reference_documents' AND tc.constraint_type = 'FOREIGN KEY'
            """)).fetchall()
            
            # Drop those foreign keys
            for table_name, constraint_name in fk_tables:
                print(f"Dropping foreign key {constraint_name} from table {table_name}")
                conn.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}"))
            
            # Drop foreign keys in the reference_documents table
            fk_constraints = conn.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'reference_documents' AND constraint_type = 'FOREIGN KEY'
            """)).fetchall()
            
            for constraint in fk_constraints:
                print(f"Dropping foreign key {constraint[0]} from reference_documents")
                conn.execute(text(f"ALTER TABLE reference_documents DROP CONSTRAINT {constraint[0]}"))
            
            conn.commit()
            
            # Drop the table
            conn.execute(text("DROP TABLE reference_documents"))
            conn.commit()
            print("Table dropped successfully.")
        
        # Create the table from the SQLAlchemy model
        print("Creating reference_documents table from model definition...")
        
        # Create the table using SQLAlchemy's metadata
        Base.metadata.create_all(engine, tables=[ReferenceDocument.__table__])
        
        print("Table created successfully.")
        
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

if __name__ == "__main__":
    try:
        recreate_reference_documents_table()
        print("\nReference documents table recreated successfully!")
    except Exception as e:
        print(f"Error recreating reference_documents table: {e}")
        sys.exit(1)
