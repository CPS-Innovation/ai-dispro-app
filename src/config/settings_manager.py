"""Settings manager with runtime configuration support.

This module provides a centralized settings broker that can:
- Load from environment variables
- Be modified at runtime
- Validate settings
- Support different environments (dev, test, prod)
"""

import os
from dataclasses import asdict, dataclass
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

from loguru import logger


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class Settings:
    """Base class for settings dataclasses."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)

@dataclass
class ApplicationSettings(Settings):
    """Application-level settings."""

    name: str = "ai-dispro"
    version: str = "test"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "DEBUG"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["environment"] = self.environment.value  # Convert Enum to string
        return data


@dataclass
class StorageSettings(Settings):
    """Storage-related settings."""

    table_name_cases: str = "cases"
    table_name_defendants: str = "defendants"
    table_name_charges: str = "charges"
    table_name_documents: str = "documents"
    table_name_versions: str = "versions"
    table_name_experiments: str = "experiments"
    table_name_sections: str = "sections"
    table_name_analysisjobs: str = "analysisjobs"
    table_name_analysisjobresults: str = "analysisjobresults"
    table_name_prompt_templates: str = "prompt_templates"
    table_name_events: str = "events"
    blob_container_name_source: str = "corpus"
    blob_container_name_processed: str = "processed"

@dataclass
class DatabaseSettings(Settings):
    """Database connection settings."""

    host: str = "********"
    port: int = 5432
    name: str = "********"
    username_secret_name: str = "********"
    password_secret_name: str = "********"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

@dataclass
class CMSSettings(Settings):
    """CMS connection settings."""

    endpoint: str = "********"
    api_key_secret_name: str = "********"
    username_secret_name: str = "********"
    password_secret_name: str = "********"

@dataclass
class AzureBlobStorageSettings(Settings):
    """Azure Blob storage connection settings."""

    account_name: str = "********"


@dataclass
class AzureDocIntelligenceSettings(Settings):
    """Azure Doc Intelligence connection settings."""

    endpoint: str = "********"
    api_version: str = "2024-11-30"
    api_key_secret_name: str = "********"


@dataclass
class AzureAIFoundrySettings(Settings):
    """Azure AI Foundry connection settings."""

    endpoint: str = "https://********.cognitiveservices.azure.com/"
    api_version: str = "2025-03-01-preview"
    deployment_name: str = "********"


@dataclass
class AzureSettings(Settings):
    """Azure service settings for Storage, Key Vault, and Application Insights."""

    key_vault_url: str = ""
    application_insights_key: str = ""


@dataclass
class TestSettings(Settings):
    """Settings specific to testing environment."""

    cms_urn: str = ""
    cms_case_id: str = ""
    blob_name: str = ""
    filepath: str = ""


class SettingsManager:
    """Centralized settings manager with runtime configuration support.

    Features:
    - Singleton pattern for global access
    - Thread-safe operations
    - Runtime configuration changes
    - Environment variable loading
    - Validation

    Usage:
        # Get instance
        settings = SettingsManager.get_instance()

        # Access settings
        db_host = settings.database.host

        # Update at runtime
        settings.update_database(host="newhost", port=5433)
    """

    _instance: Optional["SettingsManager"] = None
    _lock: Lock = Lock()

    def __init__(self):
        """Initialize settings manager.

        Note: Use get_instance() instead of direct instantiation.
        """
        self.application = ApplicationSettings()
        self.storage = StorageSettings()
        self.database = DatabaseSettings()
        self.cms = CMSSettings()
        self.blob_storage = AzureBlobStorageSettings()
        self.doc_intelligence = AzureDocIntelligenceSettings()
        self.ai_foundry = AzureAIFoundrySettings()
        self.azure = AzureSettings()
        self.test = TestSettings()
        self._change_lock = Lock()

    @classmethod
    def get_instance(cls) -> "SettingsManager":
        """Get or create the singleton instance using double-checked locking pattern.
        The double-checked locking pattern is used here for thread-safe lazy initialization:
        - First `if` check: Avoids acquiring the lock on every call (performance optimization)
        - Second `if` check: Ensures instance creation happens only once, even if multiple 
            threads pass the first check before one acquires the lock (thread-safety guarantee)

        Returns:
            SettingsManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance.load_from_env()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            cls._instance = None

    def load_from_env(self, prefix: str = "") -> None:
        """Load settings from environment variables.

        Args:
            prefix: Optional prefix for environment variables (e.g., "CPSAI_")
        """
        with self._change_lock:

            env_vars = os.environ

            logger.info(
                "Loading settings from environment variables" + (f" with prefix={prefix}" if prefix else "")
            )

            # Application settings
            app_mapping = {
                f"{prefix}APP_NAME": "name",
                f"{prefix}APP_VERSION": "version",
                f"{prefix}APP_ENVIRONMENT": "environment",
                f"{prefix}APP_DEBUG": "debug",
                f"{prefix}APP_LOG_LEVEL": "log_level",
            }

            for env_key, attr_name in app_mapping.items():
                if env_key in env_vars:
                    value = env_vars[env_key]
                    if attr_name == "environment":
                        value = Environment(value.lower())
                    elif attr_name == "debug":
                        value = value.lower() in ["true", "1", "yes"]
                    setattr(self.application, attr_name, value)

            # Storage settings
            storage_mapping = {
                f"{prefix}TABLE_NAME_CASES": "table_name_cases",
                f"{prefix}TABLE_NAME_DEFENDANTS": "table_name_defendants",
                f"{prefix}TABLE_NAME_CHARGES": "table_name_charges",
                f"{prefix}TABLE_NAME_DOCUMENTS": "table_name_documents",
                f"{prefix}TABLE_NAME_VERSIONS": "table_name_versions",
                f"{prefix}TABLE_NAME_EXPERIMENTS": "table_name_experiments",
                f"{prefix}TABLE_NAME_SECTIONS": "table_name_sections",
                f"{prefix}TABLE_NAME_ANALYSISJOBS": "table_name_analysisjobs",
                f"{prefix}TABLE_NAME_ANALYSISJOBRESULTS": "table_name_analysisjobresults",
                f"{prefix}TABLE_NAME_PROMPT_TEMPLATES": "table_name_prompt_templates",
                f"{prefix}TABLE_NAME_EVENTS": "table_name_events",
                f"{prefix}BLOB_CONTAINER_NAME_SOURCE": "blob_container_name_source",
                f"{prefix}BLOB_CONTAINER_NAME_PROCESSED": "blob_container_name_processed",
            }

            for env_key, attr_name in storage_mapping.items():
                if env_key in env_vars:
                    value = env_vars[env_key]
                    setattr(self.storage, attr_name, value)

            # Database settings
            db_mapping = {
                f"{prefix}POSTGRESQL_HOST": "host",
                f"{prefix}POSTGRESQL_PORT": "port",
                f"{prefix}POSTGRESQL_DATABASE_NAME": "name",
                f"{prefix}POSTGRESQL_USERNAME_AZURE_KEY_VAULT_SECRET_NAME": "username_secret_name",
                f"{prefix}POSTGRESQL_PASSWORD_AZURE_KEY_VAULT_SECRET_NAME": "password_secret_name",
                f"{prefix}POSTGRESQL_POOL_SIZE": "pool_size",
                f"{prefix}POSTGRESQL_MAX_OVERFLOW": "max_overflow",
                f"{prefix}POSTGRESQL_ECHO": "echo",
            }

            for env_key, attr_name in db_mapping.items():
                if env_key in os.environ:
                    value = os.environ[env_key]
                    # Type conversion
                    if attr_name in ["port", "pool_size", "max_overflow"]:
                        value = int(value)
                    elif attr_name == "echo":
                        value = value.lower() in ["true", "1", "yes"]
                    setattr(self.database, attr_name, value)
            
            # CMS settings
            cms_mapping = {
                f"{prefix}CMS_ENDPOINT": "endpoint",
                f"{prefix}CMS_API_KEY_AZURE_KEY_VAULT_SECRET_NAME": "api_key_secret_name",
                f"{prefix}CMS_USERNAME_AZURE_KEY_VAULT_SECRET_NAME": "username_secret_name",
                f"{prefix}CMS_PASSWORD_AZURE_KEY_VAULT_SECRET_NAME": "password_secret_name",
            }
            for env_key, attr_name in cms_mapping.items():
                if env_key in env_vars:
                    setattr(self.cms, attr_name, env_vars[env_key])
            
            # Azure Blob Storage settings
            blob_mapping = {
                f"{prefix}AZURE_BLOB_ACCOUNT_NAME": "account_name",
            }
            for env_key, attr_name in blob_mapping.items():
                if env_key in env_vars:
                    setattr(self.blob_storage, attr_name, env_vars[env_key])
            
            # Azure Document Intelligence settings
            docint_mapping = {
                f"{prefix}AZURE_DOC_INTELLIGENCE_ENDPOINT": "endpoint",
                f"{prefix}AZURE_DOC_INTELLIGENCE_API_VERSION": "api_version",
                f"{prefix}AZURE_DOC_INTELLIGENCE_API_KEY_KEY_VAULT_SECRET_NAME": "api_key_secret_name",
            }
            for env_key, attr_name in docint_mapping.items():
                if env_key in env_vars:
                    setattr(self.doc_intelligence, attr_name, env_vars[env_key])

            # Azure AI Foundry settings
            aif_mapping = {
                f"{prefix}AZURE_AI_FOUNDRY_ENDPOINT": "endpoint",
                f"{prefix}AZURE_AI_FOUNDRY_API_VERSION": "api_version",
                f"{prefix}AZURE_AI_FOUNDRY_DEPLOYMENT_NAME": "deployment_name",
            }
            for env_key, attr_name in aif_mapping.items():
                if env_key in env_vars:
                    setattr(self.ai_foundry, attr_name, env_vars[env_key])

            # Azure settings
            azure_mapping = {
                f"{prefix}AZURE_KEY_VAULT_URL": "key_vault_url",
                f"{prefix}AZURE_APPINSIGHTS_KEY": "application_insights_key",
            }

            for env_key, attr_name in azure_mapping.items():
                if env_key in env_vars:
                    setattr(self.azure, attr_name, env_vars[env_key])

            # Test settings
            test_mapping = {
                f"{prefix}TEST_CMS_URN": "cms_urn",
                f"{prefix}TEST_CMS_CASE_ID": "cms_case_id",
                f"{prefix}TEST_BLOB_NAME": "blob_name",
                f"{prefix}TEST_FILEPATH": "filepath",
            }

            for env_key, attr_name in test_mapping.items():
                if env_key in env_vars:
                    setattr(self.test, attr_name, env_vars[env_key])

            logger.info("Settings successfully loaded from environment")

    def export_settings(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Export all settings as a dictionary.

        Args:
            mask_secrets: If True, mask sensitive values like passwords and keys

        Returns:
            Dictionary containing all settings
        """
        settings = {
            "application": self.application.to_dict(),
            "storage": self.storage.to_dict(),
            "database": self.database.to_dict(),
            "cms": self.cms.to_dict(),
            "blob_storage": self.blob_storage.to_dict(),
            "doc_intelligence": self.doc_intelligence.to_dict(),
            "ai_foundry": self.ai_foundry.to_dict(),
            "azure": self.azure.to_dict(),
        }

        if mask_secrets:
            # Mask sensitive fields
            sensitive_fields = [
                ("database", "password_secret_name"),
                ("cms", "api_key_secret_name"),
                ("cms", "username_secret_name"),
                ("cms", "password_secret_name"),
                ("doc_intelligence", "api_key_secret_name"),
                ("azure", "application_insights_key"),
            ]
            for section, field in sensitive_fields:
                if settings[section] and settings[section][field]:
                    settings[section][field] = "***MASKED***"

        return settings

    def validate(self) -> Dict[str, List[str]]:
        """Validate current settings.

        Returns:
            Dictionary with validation errors by category
        """
        errors: Dict[str, List[str]] = {
            "application": [],
            "storage": [],
            "database": [],
            "cms": [],
            "blob_storage": [],
            "doc_intelligence": [],
            "ai_foundry": [],
            "azure": [],
        }

        # Application validation
        if not self.application.name:
            errors["application"].append("Application name is required")
        if self.application.log_level not in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]:
            errors["application"].append("Invalid log level")

        # Database validation
        if not self.database.host:
            errors["database"].append("Database host is required")
        if self.database.port < 1 or self.database.port > 65535:
            errors["database"].append("Database port must be between 1 and 65535")
        if not self.database.name:
            errors["database"].append("Database name is required")

        # Remove empty error lists
        errors = {k: v for k, v in errors.items() if v}

        return errors
    
    def is_development(self) -> bool:
        """Check if current environment is development."""
        return self.application.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if current environment is testing."""
        return self.application.environment == Environment.TESTING
    
    def is_production(self) -> bool:
        """Check if current environment is production."""
        return self.application.environment == Environment.PRODUCTION

# Convenience function for global access
def get_settings() -> SettingsManager:
    """Get the global settings manager instance.

    Returns:
        SettingsManager singleton instance
    """
    return SettingsManager.get_instance()
