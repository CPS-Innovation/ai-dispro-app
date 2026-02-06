import pytest

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