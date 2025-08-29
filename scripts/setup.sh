#!/bin/bash
echo "Setting up Plagiarism Detection System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration before running the application"
fi

echo "Setup complete!"
echo ""
echo "To start the application:"
echo "1. Edit .env file with your database and MinIO configuration"
echo "2. Run: python start.py"
echo ""
echo "Or use Docker Compose:"
echo "docker-compose up -d"
