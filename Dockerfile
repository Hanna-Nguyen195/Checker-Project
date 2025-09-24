FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# Set a default DATABASE_URL if not provided
ENV DATABASE_URL=${DATABASE_URL:-postgresql://postgres:postgres@host.docker.internal:5432/plagiarism_detector}

# Create a startup script with better error handling
RUN echo '#!/bin/bash\n\
echo "Starting application..."\n\
echo "Environment variables:"\n\
echo "DATABASE_URL: $DATABASE_URL"\n\
echo "MINIO_ENDPOINT: $MINIO_ENDPOINT"\n\
echo "PORT: $PORT"\n\
echo "RAILWAY_ENVIRONMENT_NAME: $RAILWAY_ENVIRONMENT_NAME"\n\
echo "Running database migrations..."\n\
alembic upgrade head || { echo "Migration failed"; exit 1; }\n\
echo "Starting web server..."\n\
uvicorn app.main:app --host 0.0.0.0 --port $PORT' > /app/start.sh && chmod +x /app/start.sh

# Run the startup script
CMD ["/app/start.sh"]
