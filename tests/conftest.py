"""
Pytest configuration and session-wide test fixtures.
Initializes database schema and seed data for the test suite.
"""
import pytest
from app.core.database import Base, engine, SessionLocal
import app.models  # load all models
from app.seed_data import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initializes tables and seeds test records once before test session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
