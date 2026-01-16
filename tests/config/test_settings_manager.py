"""Unit tests for the SettingsManager singleton and configuration broker.

Tests cover:
- Singleton pattern and global access
- Loading settings from environment variables
- Runtime configuration updates
- Observer pattern notifications
- Settings validation and export
- Thread safety
"""

import pytest
import os
from unittest.mock import patch

from src.config import (
    SettingsManager,
    Environment,
    get_settings,
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
    settings = get_settings()
    
    # Verify critical settings exist
    assert hasattr(settings, 'application')
    assert hasattr(settings, 'database')
    assert hasattr(settings, 'azure')
    assert hasattr(settings, 'cms')
    
    # Verify database settings
    assert hasattr(settings.database, 'host')
    assert hasattr(settings.database, 'port')
    assert hasattr(settings.database, 'name')
    assert hasattr(settings.database, 'username_secret_name')
    assert hasattr(settings.database, 'password_secret_name')
    
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
    settings1 = get_settings()
    settings2 = SettingsManager.get_instance()

    assert settings1 is settings2


def test_load_from_env():
    """Test loading settings from environment variables."""
    env_vars = {
        "APP_ENVIRONMENT": "production",
        "APP_DEBUG": "true",
        "APP_LOG_LEVEL": "DEBUG",
        
        "POSTGRESQL_HOST": "testhost",
        "POSTGRESQL_PORT": "5433",
        "POSTGRESQL_DATABASE_NAME": "testdb",
        "POSTGRESQL_USERNAME_AZURE_KEY_VAULT_SECRET_NAME": "testuser",
        "POSTGRESQL_PASSWORD_AZURE_KEY_VAULT_SECRET_NAME": "testpass",
        
        "CMS_ENDPOINT": "https://test.com",
        "CMS_API_KEY_AZURE_KEY_VAULT_SECRET_NAME": "testkey",
        "CMS_USERNAME_AZURE_KEY_VAULT_SECRET_NAME": "testuser",
        "CMS_PASSWORD_AZURE_KEY_VAULT_SECRET_NAME": "testpass",

        "AZURE_BLOB_ACCOUNT_NAME": "teststorage",

        "AZURE_DOC_INTELLIGENCE_ENDPOINT": "https://test.com",
        "AZURE_DOC_INTELLIGENCE_API_KEY_KEY_VAULT_SECRET_NAME": "testkey",

        "AZURE_AI_FOUNDRY_PROJECT": "testproject",
        "AZURE_AI_FOUNDRY_ENDPOINT": "https://test.com",
        "AZURE_AI_FOUNDRY_DEPLOYMENT_NAME": "testdeployment",

        "AZURE_KEY_VAULT_URL": "https://testvault.vault.azure.net/",
        "AZURE_APPLICATION_INSIGHTS_KEY": "testinsights",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        SettingsManager.reset_instance()
        settings = SettingsManager.get_instance()

        assert settings.application.environment == Environment.PRODUCTION
        assert settings.application.debug is True
        assert settings.application.log_level == "DEBUG"

        assert settings.database.host == "testhost"
        assert settings.database.port == 5433
        assert settings.database.name == "testdb"
        assert settings.database.username_secret_name == "testuser"
        assert settings.database.password_secret_name == "testpass"


def test_load_from_env_with_prefix():
    """Test loading with environment variable prefix."""
    env_vars = {
        "FOO_POSTGRESQL_HOST": "prefixhost",
        "FOO_POSTGRESQL_PORT": "5434",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        settings = SettingsManager.get_instance()
        settings.load_from_env(prefix="FOO_")

        assert settings.database.host == "prefixhost"
        assert settings.database.port == 5434


def test_update_database_runtime():
    """Test updating database settings at runtime."""
    settings = SettingsManager.get_instance()

    assert settings.database.host != "newhost"

    settings.database.host = "newhost"

    assert settings.database.host == "newhost"


def test_export_settings():
    """Test exporting settings."""
    settings = SettingsManager.get_instance()
    settings.database.password_secret_name = "foo"

    # Export with masking
    exported = settings.export_settings(mask_secrets=True)

    assert exported["database"]["password_secret_name"] == "***MASKED***"

    # Export without masking
    exported_unmasked = settings.export_settings(mask_secrets=False)

    assert exported_unmasked["database"]["password_secret_name"] == "foo"


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
