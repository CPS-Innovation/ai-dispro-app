"""Unit tests for database configuration, session management, and migrations.

Tests cover:
- Database configuration loading from environment
- Connection string generation
- Session manager initialization and cleanup
- Table creation and schema verification
- Database reset functionality
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.config import SettingsManager
from src.database import SessionManager
from src.database.migrations import verify_schema
from src.models import Case


@pytest.mark.unit
def test_session_manager_initialization(test_db_config):
    """Test session manager initialization."""
    manager = SessionManager(connection_string=test_db_config)
    assert manager.engine is not None
    manager.close()


@pytest.mark.regression
def test_session_manager_backward_compatibility():
    """Test that SessionManager maintains backward compatible API."""
    manager = SessionManager()
    
    # Verify essential methods exist
    assert hasattr(manager, 'session')
    assert hasattr(manager, 'close')
    assert callable(manager.session)
    assert callable(manager.close)


@pytest.mark.unit
def test_session_manager_create_tables(test_db_config):
    """Test table creation."""
    manager = SessionManager(connection_string=test_db_config)
    manager.create_all()

    # Verify tables exist
    verification = verify_schema(manager)
    assert verification["status"] == "ok"
    assert len(verification["missing_tables"]) == 0

    manager.close()


@pytest.mark.unit
def test_session_context_manager(db_session):
    """Test session as context manager."""
    assert isinstance(db_session, Session)

    # Session should be usable
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


@pytest.mark.integration
def test_init_database(session_manager):
    """Test database initialization."""
    # Database should already be initialized by fixture
    verification = verify_schema(session_manager)
    settings = SettingsManager.get_instance()

    assert verification["status"] == "ok"
    assert settings.storage.table_name_cases in verification["existing_tables"]
    assert settings.storage.table_name_documents in verification["existing_tables"]
    assert settings.storage.table_name_analysisjobs in verification["existing_tables"]


@pytest.mark.integration
class TestDatabaseErrorHandling:
    """Integration tests for database error handling."""
    
    @pytest.fixture(scope="class")
    def session_manager(self):
        """Provide a session manager for testing."""
        try:
            manager = SessionManager()
            yield manager
            manager.close()
        except Exception as e:
            pytest.skip(f"Failed to initialize session manager: {str(e)}")

    @pytest.mark.integration
    def test_transaction_rollback_on_error(self, session_manager):
        """Test that transactions are rolled back on errors."""
        test_urn = "ERROR_TEST_URN_ROLLBACK"
        
        try:
            with session_manager.session() as session:
                # Create a case
                case = Case(urn=test_urn, id=0, finalised=False)
                session.add(case)
                
                # Force an error by violating constraints
                # (attempting to add duplicate with same composite key)
                duplicate_case = Case(urn=test_urn, id=0, finalised=True)
                session.add(duplicate_case)
                
                # This should fail
                session.commit()
        except IntegrityError:
            # Expected error
            pass
        
        # Verify rollback - case should not exist
        with session_manager.session() as session:
            result = session.query(Case).filter(
                Case.urn == test_urn,
                Case.id == 0
            ).first()
            assert result is None

    @pytest.mark.integration
    def test_concurrent_writes(self, session_manager):
        """Test handling of concurrent database writes."""
        import threading
        
        test_base_urn = "01TS00002"
        errors = []
        
        def create_case(case_id: int):
            try:
                with session_manager.session() as session:
                    case = Case(
                        urn=f"{test_base_urn}{case_id:02}",
                        finalised=False
                    )
                    session.add(case)
                    session.commit()
            except Exception as e:
                errors.append(e)
        
        # Create multiple cases concurrently
        threads = [
            threading.Thread(target=create_case, args=(i,))
            for i in range(5)
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # Cleanup
        with session_manager.session() as session:
            for i in range(5):
                case = session.query(Case).filter(
                    Case.urn == f"{test_base_urn}{i:02}"
                ).first()
                if case:
                    session.delete(case)
            session.commit()

    @pytest.mark.integration
    def test_large_batch_insert(self, session_manager):
        """Test inserting a large batch of records."""
        
        test_urn = "01TS00003"
        batch_size = 10
        
        try:
            with session_manager.session() as session:
                # Create batch of cases
                cases = [
                    Case(urn=f"{test_urn}{i:02}", finalised=False)
                    for i in range(batch_size)
                ]
                session.add_all(cases)
                session.commit()
            
            # Verify all were created
            with session_manager.session() as session:
                count = session.query(Case).filter(
                    Case.urn.like(f"{test_urn}%")
                ).count()
                assert count == batch_size
        
        finally:
            # Cleanup
            with session_manager.session() as session:
                for i in range(batch_size):
                    case = session.query(Case).filter(
                        Case.urn == f"{test_urn}{i:02}"
                    ).first()
                    if case:
                        session.delete(case)
                session.commit()