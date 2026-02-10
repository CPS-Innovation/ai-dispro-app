import pytest

from .test_utilities import DatabaseSessionMockBuilder

@pytest.fixture
def mock_db_session():
    """Provide a mocked database session."""
    return DatabaseSessionMockBuilder().build()

@pytest.fixture(scope="function")
def db_session():
    """Provide a real database session for integration tests."""
    from src.database import SessionManager
    
    try:
        session_manager = SessionManager()
        session = session_manager.get_session()
        yield session
        session.close()
        session_manager.close()
    except Exception:
        # If database is not available, yield None
        yield None


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configure logging for tests."""
    from loguru import logger
    import sys
    
    # Remove default handlers
    logger.remove()
    
    # Add test-specific handler with appropriate level
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    
    yield
    
    # Cleanup
    logger.remove()
