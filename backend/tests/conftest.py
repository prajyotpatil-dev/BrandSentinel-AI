"""
Pytest configuration and shared fixtures for BrandSentinel AI tests.
"""
import pytest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.config import settings


@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine with all tables.

    StaticPool is required for SQLite in-memory databases: without it every
    new connection gets a completely separate empty database, so tables created
    by create_all() on one connection are invisible to sessions opened later.
    StaticPool forces all engine requests to reuse the same underlying
    connection, keeping a single shared in-memory database for the entire test.
    """
    from app import models

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide database session for direct database operations in tests."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def temp_storage():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "uploads"
        storage_path.mkdir()

        original_storage = settings.upload_storage_root
        settings.upload_storage_root = str(storage_path)

        yield storage_path

        settings.upload_storage_root = original_storage


@pytest.fixture(scope="function")
def client(test_engine, temp_storage):
    """
    Create test client with temporary DB and storage.

    Overrides both the FastAPI dependency *and* the global SessionLocal
    so that every code path — including the lifespan seeder and any
    service that calls SessionLocal() directly — hits the test database.
    """
    import app.database as db_module
    from app.main import app

    # Save originals
    original_session_local = db_module.SessionLocal
    original_engine = db_module.engine

    # Build test session factory
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Monkey-patch the module-level globals so that:
    #   • get_db() (used by FastAPI Depends) creates sessions on test_engine
    #   • _seed_guidelines_if_empty() (which imports SessionLocal directly) also
    #     hits the test database
    #   • init_db()'s Base.metadata.create_all(bind=engine) is harmless because
    #     we already created the tables
    db_module.SessionLocal = TestingSessionLocal
    db_module.engine = test_engine

    # Also set the FastAPI dependency override for safety
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Restore
    app.dependency_overrides.clear()
    db_module.SessionLocal = original_session_local
    db_module.engine = original_engine
