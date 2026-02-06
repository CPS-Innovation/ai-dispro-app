import re
from unittest.mock import Mock

import pytest
from sqlalchemy import inspect, text

from src.database import SessionManager, init_database, verify_schema
from src.services.azure_postgresql import get_connection_string
from src.config import (
    ApplicationSettings,
    AzureSettings,
    SettingsManager,
    DatabaseSettings,
    TestSettings,
    Environment,
)


class TestAzurePostgresConnection:

    @pytest.fixture(scope="class")
    def azure_session_manager(self):
        """Provide a session manager."""
        try:
            # Load settings from environment
            settings = SettingsManager.get_instance()
            settings.application.environment = Environment.DEVELOPMENT

            # Verify we have the necessary configuration
            if not all([
                settings.database.host,
                settings.database.port,
                settings.database.name,
                settings.database.schema,
                settings.database.username,
            ]):
                pytest.skip(
                    "Azure PostgreSQL environment variables not fully configured."
                )

            # Create session manager with settings
            manager = SessionManager()

            # Initialize database schema
            init_database(manager)

            yield manager

            # Cleanup
            manager.close()

        except Exception as e:
            pytest.skip(f"Failed to connect to Azure PostgreSQL: {str(e)}")

    @pytest.mark.integration
    def test_database_connection(self, azure_session_manager):
        session_manager = azure_session_manager
        assert session_manager.engine is not None

        verification = verify_schema(session_manager)
        assert verification["status"] == "ok"

        with session_manager.session() as session:
            result = session.execute(text("SELECT version()")).scalar()
            assert result is not None
            assert "PostgreSQL" in result

        inspector = inspect(session_manager.engine)
        existing_tables = set(inspector.get_table_names())
        assert len(existing_tables) > 0

    @pytest.mark.integration
    def test_database_crud(self, azure_session_manager):
        session_manager = azure_session_manager
        from src.repositories import ExperimentRepository
        experiement_id = 'TST-EXP-test_database_crud'
        with session_manager.get_session() as session:
            experiment_repo = ExperimentRepository(session)
            # Create
            experiment = experiment_repo.create(id=experiement_id)
            assert experiment.id == experiement_id
            session.commit()
            # Read
            fetched = experiment_repo.get_by_id(experiement_id)
            assert fetched is not None
            assert fetched.id == experiement_id
            # Update
            experiment.finalised = True
            session.commit()
            updated = experiment_repo.get_by_id(experiement_id)
            assert updated.finalised is True
            # Delete
            experiment_repo.delete(experiement_id)
            session.commit()
            experiment_none = experiment_repo.get_by_id(experiement_id)
            assert experiment_none is None


class TestConnectionString:
    """Tests for get_connection_string function."""

    @pytest.fixture(scope="class")
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock(spec=SettingsManager)
        settings.application = Mock(spec=ApplicationSettings)
        settings.database = Mock(spec=DatabaseSettings)
        settings.test = Mock(spec=TestSettings)
        settings.database.host = "test-host.postgres.database.azure.com"
        settings.database.port = 5432
        settings.database.name = "test_db"
        settings.test.postgresql_username = "test_user"
        settings.database.username_secret_name = "db-user"
        settings.azure = Mock(spec=AzureSettings)
        settings.is_development = lambda: settings.application.environment == Environment.DEVELOPMENT
        settings.is_testing = lambda: settings.application.environment == Environment.TESTING
        settings.is_production = lambda: settings.application.environment == Environment.PRODUCTION
        return settings

    @pytest.mark.unit
    @pytest.mark.parametrize("pattern,description", [
        (r"^postgresql\+psycopg2://", "PostgreSQL driver with psycopg2"),
        (r"://.*@.*:\d+/.*", "Complete URL structure"),
        (r"sslmode=require$", "SSL requirement at end"),
    ])
    def test_connection_string_format_regex_patterns(self, mock_settings, pattern, description):
        """Test connection string matches expected regex patterns."""
        mock_settings.application.environment = Environment.DEVELOPMENT
        connection_string = get_connection_string(mock_settings)
        assert re.search(pattern, connection_string), f"Pattern '{description}' not found in: {connection_string}"
