#!/bin/bash
# Exit on error
set -e

# Print commands before executing
set -x

echo "==================== STARTUP SCRIPT ==================="
echo "Current directory: $(pwd)"
echo "Directory contents: $(ls -la)"
echo "Python version: $(python --version)"
echo "Alembic version: $(python -m alembic --version)"

echo "🔄 Checking for RAILWAY_RESET_DB environment variable..."
if [ "$RAILWAY_RESET_DB" = "true" ]; then
    echo "🗑️ Resetting database (dropping all tables)..."
    python scripts/reset_db.py
    echo "✅ Database reset completed"
else
    echo "⏭️ Skipping database reset (RAILWAY_RESET_DB not set to true)"
    echo "🔄 Running regular migrations..."
    
    # Try different approaches to run migrations
    echo "Attempting migration with python -m alembic..."
    python -m alembic upgrade head || {
        echo "Failed with python -m alembic, trying with alembic directly..."
        alembic upgrade head || {
            echo "Failed with direct alembic command, trying with absolute path..."
            python $(which alembic) upgrade head || {
                echo "All migration attempts failed. Continuing anyway..."
            }
        }
    }
    
    echo "Migration attempts completed"
fi

echo "🚀 Starting application..."
# Use PORT from environment variable or default to 8000
PORT=${PORT:-8000}
echo "Using port: $PORT"

# Start the application
echo "Starting uvicorn server..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT

