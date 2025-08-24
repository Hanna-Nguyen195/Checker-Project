#!/usr/bin/env python3
"""
Startup script for the Plagiarism Detection System.
This script handles database initialization and starts the FastAPI server.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config.settings import get_settings
from app.config.database import create_tables, engine
from app.utils.logger import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


def check_database_connection():
    """Check if database is accessible."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False


def initialize_database():
    """Initialize database tables."""
    try:
        create_tables()
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        return False


def create_admin_user():
    """Create default admin user if it doesn't exist."""
    try:
        from app.config.database import SessionLocal
        from app.services.user_service import UserService
        from app.schemas.user import UserCreate
        
        db = SessionLocal()
        try:
            user_service = UserService(db)
            
            # Check if admin user exists
            admin_user = user_service.get_user_by_username("admin")
            if not admin_user:
                admin_data = UserCreate(
                    username="admin",
                    email="admin@example.com",
                    password="admin123!",
                    full_name="System Administrator",
                    role="admin"
                )
                user_service.create_user(admin_data)
                logger.info("Default admin user created (username: admin, password: admin123!)")
            else:
                logger.info("Admin user already exists")
        finally:
            db.close()
        
        return True
    except Exception as e:
        logger.error("Failed to create admin user", error=str(e))
        return False


def main():
    """Main startup function."""
    logger.info("Starting Plagiarism Detection System", version=settings.app_version)
    
    # Check database connection
    if not check_database_connection():
        logger.error("Cannot connect to database. Please check your configuration.")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database.")
        sys.exit(1)
    
    # Create admin user
    if not create_admin_user():
        logger.warning("Failed to create admin user, but continuing...")
    
    # Start the server
    logger.info("Starting FastAPI server", host="0.0.0.0", port=8000)
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
