#!/bin/bash
set -e

echo "🔄 Checking for RAILWAY_RESET_DB environment variable..."
if [ "$RAILWAY_RESET_DB" = "true" ]; then
    echo "🗑️ Resetting database (dropping all tables)..."
    python scripts/reset_db.py
    echo "✅ Database reset completed"
else
    echo "⏭️ Skipping database reset (RAILWAY_RESET_DB not set to true)"
    echo "🔄 Running regular migrations..."
    python -m alembic upgrade head
fi

echo "🚀 Starting application..."
# Use PORT from environment variable or default to 8000
PORT=${PORT:-8000}
echo "Using port: $PORT"
uvicorn app.main:app --host 0.0.0.0 --port $PORT
