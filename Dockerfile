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

# Make scripts executable
RUN chmod +x reset_and_start.sh
RUN chmod +x scripts/reset_db.py

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Run migrations and start the application
# Make sure the script is executable
RUN chmod +x /app/reset_and_start.sh

# Use ENTRYPOINT to ensure the script runs
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["./reset_and_start.sh"]
