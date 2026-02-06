import pytest
import os
from unittest.mock import patch

from src.config import (
    SettingsManager,
    Environment,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    # clears any leftover state from previous tests
    SettingsManager.reset_instance()
    yield  # test runs here
    # clean up after test
    SettingsManager.reset_instance()

def test_environment_enum_backward_compatibility():
    """Test that Environment enum values remain stable."""
    assert hasattr(Environment, 'DEVELOPMENT')
    assert hasattr(Environment, 'TESTING')
    assert hasattr(Environment, 'PRODUCTION')

def test_settings_backward_compatibility():
    """Test that settings structure remains compatible."""
    settings = SettingsManager.get_instance()
    
    # Verify critical settings exist
    assert hasattr(settings, 'application')
    assert hasattr(settings, 'database')
    assert hasattr(settings, 'azure')
    assert hasattr(settings, 'cms')
    
    # Verify database settings
    assert hasattr(settings.database, 'host')
    assert hasattr(settings.database, 'port')
    assert hasattr(settings.database, 'name')
    assert hasattr(settings.database, 'username')
    
    # Verify environment methods
    assert callable(settings.is_development)
    assert callable(settings.is_testing)
    assert callable(settings.is_production)


def test_singleton_pattern():
    """Test that SettingsManager is a singleton."""
    settings1 = SettingsManager.get_instance()
    settings2 = SettingsManager.get_instance()

    assert settings1 is settings2


def test_get_settings_convenience():
    """Test convenience function."""
    settings1 = SettingsManager.get_instance()
    settings2 = SettingsManager.get_instance()

    assert settings1 is settings2


def test_load_from_env():
    """Test loading settings from environment variables."""
    env_vars = {
        "POSTGRESQL_HOST": "testhost",
        "POSTGRESQL_PORT": "5433",
        "POSTGRESQL_DATABASE_NAME": "testdb",
        "POSTGRESQL_USERNAME": "testuser",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        SettingsManager.reset_instance()
        settings = SettingsManager.get_instance()
        
        assert settings.database.host == "testhost"
        assert settings.database.port == 5433
        assert settings.database.name == "testdb"
        assert settings.database.username == "testuser"


def test_update_database_runtime():
    """Test updating database settings at runtime."""
    settings = SettingsManager.get_instance()

    assert settings.database.host != "newhost"

    settings.database.host = "newhost"

    assert settings.database.host == "newhost"


def test_export_settings():
    """Test exporting settings."""
    settings = SettingsManager.get_instance()
    settings.cms.username_secret_name = "foo"

    # Export with masking
    exported = settings.export_settings(mask_secrets=True)
    assert exported["cms"]["username_secret_name"] == "***MASKED***"

    # Export without masking
    exported_unmasked = settings.export_settings(mask_secrets=False)

    assert exported_unmasked["cms"]["username_secret_name"] == "foo"


def test_validate_settings():
    """Test settings validation."""
    settings = SettingsManager.get_instance()

    # Valid settings
    errors = settings.validate()
    assert len(errors) == 0

    # Invalid settings
    settings.database.host=""
    settings.database.port=99999

    errors = settings.validate()

    assert "database" in errors
    assert len(errors["database"]) >= 2


def test_environment_checks():
    """Test environment check methods."""
    settings = SettingsManager.get_instance()

    # Save current environment
    original_env = settings.application.environment

    try:
        # Test environment changes
        settings.application.environment = Environment.DEVELOPMENT
        assert settings.is_development() is True
        assert settings.is_production() is False
        assert settings.is_testing() is False

        settings.application.environment = Environment.TESTING
        assert settings.is_development() is False
        assert settings.is_testing() is True
        assert settings.is_production() is False

        settings.application.environment = Environment.PRODUCTION
        assert settings.is_development() is False
        assert settings.is_testing() is False
        assert settings.is_production() is True
    finally:
        # Restore original environment
        settings.application.environment = original_env


def test_thread_safety():
    """Test thread-safe operations."""
    import threading

    settings = SettingsManager.get_instance()
    results = []

    def update_settings(value):
        settings.database.host = f"host{value}"
        results.append(settings.database.host)

    threads = [threading.Thread(target=update_settings, args=(i,)) for i in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # All updates should have completed
    assert len(results) == 10
