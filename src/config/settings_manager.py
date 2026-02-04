from typing import Optional
import os
from dataclasses import asdict, dataclass
from enum import Enum
from threading import Lock
from typing import Any

from loguru import logger


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class Settings:
    """Base class for settings dataclasses."""

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)

@dataclass
class ApplicationSettings(Settings):
    """Application-level settings."""

    name: str = "ai-dispro"
    version: str = "test"
    environment: Environment = Environment.DEVELOPMENT
    
    def to_dict(self) -> dict[str, Any]:
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
    table_name_analysisresults: str = "analysisresults"
    table_name_prompt_templates: str = "prompt_templates"
    table_name_events: str = "events"
    blob_container_name_source: str = "corpus"
    blob_container_name_processed: str = "processed"
    blob_container_name_section: str = "processed"


@dataclass
class DatabaseSettings(Settings):
    """Database connection settings."""

    host: str = "********"
    port: int = 5432
    name: str = "********"
    schema: str = "********"
    username: str = "********"
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


@dataclass
class TestSettings(Settings):
    """Settings specific to testing environment."""

    cms_urn: str = ""
    cms_case_id: str = ""
    blob_name: str = ""
    filepath: str = ""
    section_content: str = ""
    experiment_id: str = ""
    section_id: str = ""
    theme: str = ""
    pattern: str = ""


class SettingsManager:
    """Centralized settings manager with runtime configuration support."""

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

    def load_from_env(self) -> None:
        """Load settings from environment variables."""
        with self._change_lock:

            env_vars = os.environ

            logger.info("Loading settings from environment variables")

            # Application settings
            app_mapping = {
                "APP_ENVIRONMENT": "environment",
            }

            for env_key, attr_name in app_mapping.items():
                if env_key in env_vars:
                    value = env_vars[env_key]
                    if attr_name == "environment":
                        value = Environment(value.lower())
                    setattr(self.application, attr_name, value)

            # Storage settings
            storage_mapping = {
                "TABLE_NAME_CASES": "table_name_cases",
                "TABLE_NAME_DEFENDANTS": "table_name_defendants",
                "TABLE_NAME_CHARGES": "table_name_charges",
                "TABLE_NAME_DOCUMENTS": "table_name_documents",
                "TABLE_NAME_VERSIONS": "table_name_versions",
                "TABLE_NAME_EXPERIMENTS": "table_name_experiments",
                "TABLE_NAME_SECTIONS": "table_name_sections",
                "TABLE_NAME_ANALYSISJOBS": "table_name_analysisjobs",
                "TABLE_NAME_ANALYSISRESULTS": "table_name_analysisresults",
                "TABLE_NAME_PROMPT_TEMPLATES": "table_name_prompt_templates",
                "TABLE_NAME_EVENTS": "table_name_events",
                "BLOB_CONTAINER_NAME_SOURCE": "blob_container_name_source",
                "BLOB_CONTAINER_NAME_PROCESSED": "blob_container_name_processed",
                "BLOB_CONTAINER_NAME_SECTION": "blob_container_name_section",
            }

            for env_key, attr_name in storage_mapping.items():
                if env_key in env_vars:
                    value = env_vars[env_key]
                    setattr(self.storage, attr_name, value)

            # Database settings
            db_mapping = {
                "POSTGRESQL_HOST": "host",
                "POSTGRESQL_PORT": "port",
                "POSTGRESQL_DATABASE_NAME": "name",
                "POSTGRESQL_SCHEMA": "schema",
                "POSTGRESQL_USERNAME": "username",
            }

            for env_key, attr_name in db_mapping.items():
                if env_key in os.environ:
                    value = os.environ[env_key]
                    # Type conversion
                    if attr_name == "port":
                        value = int(value)
                    setattr(self.database, attr_name, value)
            
            # CMS settings
            cms_mapping = {
                "CMS_ENDPOINT": "endpoint",
                "CMS_API_KEY_AZURE_KEY_VAULT_SECRET_NAME": "api_key_secret_name",
                "CMS_USERNAME_AZURE_KEY_VAULT_SECRET_NAME": "username_secret_name",
                "CMS_PASSWORD_AZURE_KEY_VAULT_SECRET_NAME": "password_secret_name",
            }
            for env_key, attr_name in cms_mapping.items():
                if env_key in env_vars:
                    setattr(self.cms, attr_name, env_vars[env_key])
            
            # Azure Blob Storage settings
            blob_mapping = {
                "AZURE_BLOB_ACCOUNT_NAME": "account_name",
            }
            for env_key, attr_name in blob_mapping.items():
                if env_key in env_vars:
                    setattr(self.blob_storage, attr_name, env_vars[env_key])
            
            # Azure Document Intelligence settings
            docint_mapping = {
                "AZURE_DOC_INTELLIGENCE_ENDPOINT": "endpoint",
                "AZURE_DOC_INTELLIGENCE_API_VERSION": "api_version",
            }
            for env_key, attr_name in docint_mapping.items():
                if env_key in env_vars:
                    setattr(self.doc_intelligence, attr_name, env_vars[env_key])

            # Azure AI Foundry settings
            aif_mapping = {
                "AZURE_AI_FOUNDRY_ENDPOINT": "endpoint",
                "AZURE_AI_FOUNDRY_API_VERSION": "api_version",
                "AZURE_AI_FOUNDRY_DEPLOYMENT_NAME": "deployment_name",
            }
            for env_key, attr_name in aif_mapping.items():
                if env_key in env_vars:
                    setattr(self.ai_foundry, attr_name, env_vars[env_key])

            # Azure settings
            azure_mapping = {
                "AZURE_KEY_VAULT_URL": "key_vault_url",
            }

            for env_key, attr_name in azure_mapping.items():
                if env_key in env_vars:
                    setattr(self.azure, attr_name, env_vars[env_key])

            # Test settings
            test_mapping = {
                "TEST_CMS_URN": "cms_urn",
                "TEST_CMS_CASE_ID": "cms_case_id",
                "TEST_BLOB_NAME": "blob_name",
                "TEST_FILEPATH": "filepath",
                "TEST_SECTION_CONTENT": "section_content",
                "TEST_EXPERIMENT_ID": "experiment_id",
                "TEST_SECTION_ID": "section_id",
                "TEST_THEME": "theme",
                "TEST_PATTERN": "pattern",
            }

            for env_key, attr_name in test_mapping.items():
                if env_key in env_vars:
                    setattr(self.test, attr_name, env_vars[env_key])

            logger.info("Settings successfully loaded from environment")

    def export_settings(self, mask_secrets: bool = True) -> dict[str, Any]:
        """Export all settings as a dictionary.

        Args:
            mask_secrets: If True, mask sensitive values like passwords and keys
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
            "test": self.test.to_dict(),
        }

        if mask_secrets:
            # Mask sensitive fields
            sensitive_fields = [
                ("cms", "api_key_secret_name"),
                ("cms", "username_secret_name"),
                ("cms", "password_secret_name"),
            ]
            for section, field in sensitive_fields:
                if settings[section] and settings[section][field]:
                    settings[section][field] = "***MASKED***"

        return settings

    def validate(self) -> dict[str, list[str]]:
        """Validate current settings.

        Returns:
            Dictionary with validation errors by category
        """
        errors: dict[str, list[str]] = {
            "application": [],
            "storage": [],
            "database": [],
            "cms": [],
            "blob_storage": [],
            "doc_intelligence": [],
            "ai_foundry": [],
            "azure": [],
            "test": [],
        }

        # Application validation
        ...

        # Database validation
        if not self.database.host:
            errors["database"].append("Database host is required")
        if self.database.port < 1 or self.database.port > 65535:
            errors["database"].append("Database port must be between 1 and 65535")
        if not self.database.name:
            errors["database"].append("Database name is required")
        if not self.database.schema:
            errors["database"].append("Database schema is required")

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
