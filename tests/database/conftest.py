"""Pytest configuration and shared test fixtures.

Responsibilities:
- Provide database fixtures with in-memory SQLite
- Create isolated test sessions with automatic cleanup
- Configure session managers for testing
All fixtures use SQLite for fast, isolated tests.
"""

import pytest

from src.database import SessionManager
from src.database.migrations import init_database


@pytest.fixture(scope="session")
def test_db_config():
    """Database configuration for testing (SQLite in-memory)."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session(test_db_config):
    """Provide a database session for testing with automatic rollback.

    This fixture:
    1. Creates a new SQLite in-memory database for each test
    2. Creates all tables
    3. Provides a session
    4. Tears down after the test
    """
    # Initialize session manager with test database
    session_manager = SessionManager(connection_string=test_db_config)

    # Create all tables
    init_database(session_manager)

    # Create a session
    session = session_manager.get_session()

    try:
        yield session
    finally:
        session.close()
        session_manager.close()


@pytest.fixture(scope="function")
def session_manager(test_db_config):
    """Provide a session manager for testing."""
    manager = SessionManager(connection_string=test_db_config)
    init_database(manager)

    try:
        yield manager
    finally:
        manager.close()
