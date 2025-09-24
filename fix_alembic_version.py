#!/usr/bin/env python3
"""
Script to fix the alembic_version table in the database.
This will update the version_num to match the latest migration in your project.
"""

import sys
from sqlalchemy import create_engine, text
from app.config.settings import get_settings

def fix_alembic_version():
    """Fix the alembic_version table to match the actual migration history."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    # The correct revision ID from your migration files
    correct_revision = 'c2fddd1bb760'  # create_three_database_structure
    
    with engine.connect() as conn:
        # Check current version
        result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        if result:
            current_version = result[0]
            print(f"Current alembic version: {current_version}")
            
            # Update to correct version
            conn.execute(text(f"UPDATE alembic_version SET version_num = '{correct_revision}'"))
            conn.commit()
            print(f"Updated alembic version to: {correct_revision}")
        else:
            # If no version exists, insert it
            conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{correct_revision}')"))
            conn.commit()
            print(f"Inserted alembic version: {correct_revision}")

if __name__ == "__main__":
    try:
        fix_alembic_version()
        print("Alembic version fixed successfully!")
    except Exception as e:
        print(f"Error fixing alembic version: {e}")
        sys.exit(1)
