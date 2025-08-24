import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient

# Set test environment variables before importing app
os.environ.update({
    "DATABASE_URL": "sqlite:///./test.db",
    "DATABASE_USER": "test",
    "DATABASE_PASSWORD": "test",
    "SECRET_KEY": "test-secret-key",
    "MINIO_ENDPOINT": "localhost:9002",
    "MINIO_ACCESS_KEY": "testadmin",
    "MINIO_SECRET_KEY": "testadmin123",
    "ENVIRONMENT": "test"
})

from app.main import app
from app.config.database import get_db, Base
from app.core.security import create_access_token
from app.models.user import User
from app.services.user_service import UserService
from app.config.settings import get_settings
from app.services.storage_service import StorageService
from app.schemas.user import UserCreate

settings = get_settings()

# Create test database engine (use SQLite for tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def setup_test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(setup_test_db) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(setup_test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "full_name": "Test User"
    }


@pytest.fixture
def test_admin_data():
    """Test admin user data."""
    return {
        "username": "testadmin",
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "full_name": "Test Admin",
        "role": "admin"
    }


@pytest.fixture
def create_test_user(db_session, test_user_data):
    """Create a test user in database."""
    user_service = UserService(db_session)
    user_create = UserCreate(**test_user_data)
    user = user_service.create_user(user_create)
    return user


@pytest.fixture
def create_test_admin(db_session, test_admin_data):
    """Create a test admin user in database."""
    user_service = UserService(db_session)
    admin_create = UserCreate(**test_admin_data)
    admin = user_service.create_user(admin_create)
    return admin


@pytest.fixture
def auth_headers(client, create_test_user):
    """Get authentication headers for test user."""
    response = client.post(
        "/auth/login",
        data={
            "username": create_test_user.username,
            "password": "TestPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, create_test_admin):
    """Get authentication headers for admin user."""
    response = client.post(
        "/auth/login",
        data={
            "username": create_test_admin.username,
            "password": "AdminPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    
    # Cleanup
    try:
        os.unlink(f.name)
    except:
        pass


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    content = "This is a sample document for plagiarism testing. It contains some text that can be used to test the plagiarism detection functionality."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    
    # Cleanup
    try:
        os.unlink(f.name)
    except:
        pass


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def storage_service():
    """Create storage service instance."""
    return StorageService()
