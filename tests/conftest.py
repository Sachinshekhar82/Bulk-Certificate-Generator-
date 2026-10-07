import os
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.certificate_service import certificate_generator

# In-memory SQLite with StaticPool so all connections share the same memory database
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Set up temporary storage directory for tests."""
    temp_storage = tmp_path_factory.mktemp("cert_storage")
    settings.STORAGE_DIR = str(temp_storage)
    certificate_generator.storage_dir = Path(str(temp_storage))
    yield
    # Cleanup handled automatically by pytest


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a transactional database session for tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient configured with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Monkeypatch the background worker session factory so background tasks use test DB
    import app.api.v1.routes as routes_module
    from app.services import job_processor

    original_factory = job_processor.SessionLocal
    job_processor.SessionLocal = TestingSessionLocal

    with TestClient(app) as test_client:
        yield test_client

    job_processor.SessionLocal = original_factory
    app.dependency_overrides.clear()
