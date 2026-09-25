import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app
from backend.database import Base, get_db
from backend.seed_data import seed_users

from sqlalchemy.pool import StaticPool

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def setup_database():
    """Create tables and seed data once per test."""
    # Disable the app startup events that seed the real database
    app.router.on_startup.clear()
    
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_users(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(setup_database):
    """Return a TestClient instance."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db_session(setup_database):
    """Return a fresh database session for a single test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
