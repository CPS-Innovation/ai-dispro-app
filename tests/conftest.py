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


@pytest.fixture(scope="session")
def seed_test_blob():
    """Seed the test document blob in the source container.

    Blob-ingestion integration tests read ``settings.test.blob_name`` from the
    source container. This uploads a minimal valid PDF there before the tests
    run and removes it afterwards, so the suite does not depend on pre-existing
    storage state. Skips when no test blob name is configured.
    """
    from src.config import SettingsManager
    from src.services import get_blob_service_client, save_blob
    from src.services.azure_docintel import minimal_pdf

    settings = SettingsManager.get_instance()
    blob_name = settings.test.blob_name
    container = settings.storage.blob_container_name_source

    if not blob_name:
        pytest.skip("settings.test.blob_name is not configured")

    save_blob(container_name=container, blob_name=blob_name, data=minimal_pdf())
    try:
        yield blob_name
    finally:
        # Best-effort cleanup so the seeded blob does not linger between runs.
        try:
            with get_blob_service_client() as client:
                client.get_blob_client(container=container, blob=blob_name).delete_blob()
        except Exception:
            pass


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
