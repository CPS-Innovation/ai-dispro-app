from loguru import logger
from sqlalchemy import inspect

from .base import Base
from .session import SessionManager, get_session_manager


def init_database(session_manager: SessionManager | None = None) -> None:
    """Initialize database by creating all tables.
    
    This is the primary method for setting up the database schema.
    Safe to call multiple times - will only create missing tables.
    
    Usage:
        from src.database import init_session_manager, init_database
        init_session_manager()  # Set up session manager
        init_database()  # Create tables
    """
    if session_manager is None:
        session_manager = get_session_manager()
    
    logger.info("Initializing database schema...")
    session_manager.create_all()
    logger.info("Database schema initialized successfully")


def verify_schema(session_manager: SessionManager | None = None) -> dict:
    """Verify that all expected tables exist in the database.
    
    Returns:
        Dictionary with verification results:
        {
            'status': 'ok' | 'missing_tables' | 'error',
            'expected_tables': list of expected table names,
            'existing_tables': list of existing table names,
            'missing_tables': list of missing table names (if any)
        }
    """
    if session_manager is None:
        session_manager = get_session_manager()
    
    try:
        # Get expected tables from models
        expected_tables = set(Base.metadata.tables.keys())
        
        # Get existing tables from database
        inspector = inspect(session_manager.engine)
        existing_tables = set(inspector.get_table_names())
        
        # Check for missing tables
        missing_tables = expected_tables - existing_tables
        
        result = {
            'expected_tables': sorted(expected_tables),
            'existing_tables': sorted(existing_tables),
            'missing_tables': sorted(missing_tables),
            'status': 'ok' if not missing_tables else 'missing_tables'
        }
        
        if missing_tables:
            logger.warning("Missing tables in database: {}", missing_tables)
        else:
            logger.info("Database schema verification passed")
        
        return result
        
    except Exception as e:
        logger.error("Error verifying schema: {}", e)
        return {
            'status': 'error',
            'error': str(e),
            'expected_tables': sorted(Base.metadata.tables.keys()),
            'existing_tables': [],
            'missing_tables': []
        }
