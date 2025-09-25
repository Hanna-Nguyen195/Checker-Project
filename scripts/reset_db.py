#!/usr/bin/env python3
"""
Database reset script for the Plagiarism Detection System.
This script drops all tables and recreates them from scratch using Alembic migrations.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import get_settings
from app.config.database import engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def drop_all_tables():
    """Drop all tables in the database."""
    try:
        # Get a connection
        with engine.connect() as conn:
            try:
                # Disable foreign key checks temporarily
                conn.execute(text("SET session_replication_role = 'replica';"))
                
                # Get all table names
                result = conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' AND tablename != 'alembic_version';
                """))
                tables = [row[0] for row in result]
                
                logger.info(f"Found {len(tables)} tables to drop")
                
                # Drop each table
                for table in tables:
                    logger.info(f"Dropping table: {table}")
                    try:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
                    except Exception as table_error:
                        logger.error(f"Error dropping table {table}: {table_error}")
                
                # Also drop the alembic_version table to reset migration history
                try:
                    conn.execute(text('DROP TABLE IF EXISTS "alembic_version" CASCADE;'))
                    logger.info("Dropped alembic_version table")
                except Exception as alembic_error:
                    logger.error(f"Error dropping alembic_version table: {alembic_error}")
                
                # Re-enable foreign key checks
                conn.execute(text("SET session_replication_role = 'origin';"))
                
                # Commit the transaction
                conn.commit()
                logger.info("All tables dropped successfully")
                return True
            except Exception as inner_error:
                logger.error(f"Error during table dropping process: {inner_error}")
                conn.rollback()
                return False
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

def run_migrations():
    """Run all migrations from scratch."""
    try:
        logger.info("Running migrations from scratch")
        
        # First try using the alembic module directly
        try:
            logger.info("Attempting to run migrations using Python module")
            from alembic.config import Config
            from alembic import command
            
            # Load the alembic configuration
            alembic_cfg = Config("alembic.ini")
            
            # Run the migration
            command.upgrade(alembic_cfg, "head")
            logger.info("Migrations completed successfully using Python module")
            return True
        except Exception as module_error:
            logger.warning(f"Failed to run migrations using Python module: {module_error}")
            logger.info("Falling back to subprocess method")
            
            # Fall back to subprocess method
            result = subprocess.run(["python", "-m", "alembic", "upgrade", "head"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Migrations completed successfully using subprocess")
                return True
            else:
                logger.error(f"Migration failed: {result.stderr}")
                return False
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        return False

def main():
    """Main function to reset the database."""
    logger.info("Starting database reset")
    
    # Check if we're in production/Railway
    settings = get_settings()
    is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT_NAME"))
    
    if is_railway:
        logger.info("Railway environment detected")
    else:
        logger.info("Local environment detected")
    
    # Drop all tables
    if drop_all_tables():
        # Run migrations
        if run_migrations():
            logger.info("Database reset completed successfully")
            return 0
        else:
            logger.error("Failed to run migrations")
            return 1
    else:
        logger.error("Failed to drop tables")
        return 1

if __name__ == "__main__":
    sys.exit(main())
