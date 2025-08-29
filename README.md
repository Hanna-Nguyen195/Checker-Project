# Plagiarism Detection System

A comprehensive FastAPI-based plagiarism detection system with PostgreSQL database and MinIO object storage.

## Features

### User Features
- **Document Upload**: Upload documents for plagiarism checking
- **Plagiarism Analysis**: Get detailed similarity reports with sentence-level matches
- **Document Download**: Download original documents and reports
- **Payment Integration**: Subscription-based access with different plans
- **History Tracking**: View plagiarism check history
- **Document Requests**: Request additional documents to be added to the reference database

### Admin Features
- **System Statistics**: View total users, documents uploaded, and system metrics
- **Document Management**: Manage reference documents in the database
- **User Management**: Manage user accounts and permissions
- **Document Approval**: Review and approve user-submitted documents for database inclusion
- **Analytics Dashboard**: Comprehensive system analytics

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **Object Storage**: MinIO
- **Caching**: Redis (optional)
- **Authentication**: JWT tokens with bcrypt password hashing
- **Containerization**: Docker & Docker Compose
- **Logging**: Structured logging with structlog

## Project Structure

```
plagiarism-detector/
├── app/
│   ├── config/          # Configuration and database setup
│   ├── core/            # Security, middleware, dependencies
│   ├── models/          # SQLAlchemy database models
│   ├── schemas/         # Pydantic validation schemas
│   ├── services/        # Business logic layer
│   ├── controllers/     # API route handlers
│   └── utils/           # Utility functions and helpers
├── init-scripts/        # Database initialization scripts
├── docker-compose.yml   # Docker services configuration
├── Dockerfile          # Application container
└── requirements.txt    # Python dependencies
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

1. **Clone and setup environment**:
   ```bash
   git clone <repository>
   cd plagiarism-detector
   cp .env.example .env
   ```

2. **Configure environment variables** in `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/plagiarism_detector
   SECRET_KEY=your-super-secret-jwt-key-change-in-production
   MINIO_ENDPOINT=minio:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin123
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**:
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Access the application**:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (admin/admin123)

### Local Development

1. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and MinIO** (using Docker):
   ```bash
   docker-compose up -d postgres minio redis
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Common Commands

### Development Server
```bash
# Start development server with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative: using the startup script
python start.py

# Or directly run the app module
python -m app.main
```

### Testing
```bash
# Run all tests
python scripts/run_tests.py

# Run specific test types
python scripts/run_tests.py unit          # Unit tests only
python scripts/run_tests.py integration   # Integration tests only
python scripts/run_tests.py e2e          # End-to-end tests only

# Run tests with coverage
python scripts/run_tests.py --coverage

# Run tests without starting Docker services
python scripts/run_tests.py --no-services

# Keep test services running after tests
python scripts/run_tests.py --keep-services
```

### Database Management
```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current migration status
alembic current

# Show migration history
alembic history
```

### Docker Operations
```bash
# Start all services
docker-compose up -d

# Start only specific services
docker-compose up -d postgres minio redis

# View logs
docker-compose logs -f api
docker-compose logs -f postgres

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Start test environment
docker-compose -f docker-compose.test.yml up -d
```

### Code Quality
```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
pylint app/

# Type checking
mypy app/

# Security check
bandit -r app/
```

### Environment Setup
```bash
# Windows setup
scripts\setup.bat

# Linux/Mac setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# Copy environment template
cp .env.example .env
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Refresh access token
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token

### User Management
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update current user profile
- `POST /users/change-password` - Change password

### Document Management
- `POST /documents/upload` - Upload document for checking
- `GET /documents` - List user documents
- `GET /documents/{id}` - Get document details
- `GET /documents/{id}/download` - Download document
- `DELETE /documents/{id}` - Delete document

### Plagiarism Checking
- `POST /plagiarism/check` - Start plagiarism check
- `GET /plagiarism/checks` - List plagiarism checks
- `GET /plagiarism/checks/{id}` - Get check details
- `GET /plagiarism/checks/{id}/report` - Download detailed report

### Admin Endpoints
- `GET /admin/stats` - System statistics
- `GET /admin/users` - List all users
- `PUT /admin/users/{id}` - Update user
- `GET /admin/documents/pending` - List pending document approvals
- `POST /admin/documents/{id}/approve` - Approve document
- `POST /admin/documents/{id}/reject` - Reject document

## Database Schema

The system uses the following main entities:
- **Users**: User accounts and authentication
- **Reference Documents**: Approved documents for plagiarism comparison
- **User Documents**: Documents uploaded by users
- **Plagiarism Checks**: Plagiarism analysis results
- **Plagiarism Matches**: Document-level similarity matches
- **Sentence Matches**: Sentence-level similarity details
- **Plans**: Subscription plans
- **User Plans**: User subscription management
- **System Stats**: System analytics and metrics

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **Role-Based Access Control**: User and admin roles
- **Input Validation**: Comprehensive request validation
- **File Upload Security**: File type and size validation
- **CORS Protection**: Configurable CORS policies
- **Request Logging**: Comprehensive request/response logging

## Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# JWT Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MinIO Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=plagiarism-documents

# File Upload
MAX_FILE_SIZE=52428800  # 50MB
ALLOWED_FILE_TYPES=application/pdf,application/msword,text/plain

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality
```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

## Production Deployment

1. **Security**: Change all default passwords and secrets
2. **SSL/TLS**: Use HTTPS in production
3. **Database**: Use managed PostgreSQL service
4. **Storage**: Use cloud object storage (AWS S3, etc.)
5. **Monitoring**: Add application monitoring and alerting
6. **Backup**: Implement database and storage backups

## License

This project is licensed under the MIT License.
