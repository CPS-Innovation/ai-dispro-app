"""Configuration management with runtime settings broker.

Responsibilities:
- Singleton settings manager for global configuration access
- Runtime configuration updates with observer notifications
- Settings loading from environment variables
- Thread-safe configuration management
"""

from .settings_manager import (
    ApplicationSettings,
    StorageSettings,
    DatabaseSettings,
    CMSSettings,
    AzureBlobStorageSettings,
    AzureDocIntelligenceSettings,
    AzureAIFoundrySettings,
    AzureSettings,
    Environment,
    SettingsManager,
    get_settings,
)

__all__ = [
    "SettingsManager",
    "ApplicationSettings",
    "StorageSettings",
    "DatabaseSettings",
    "CMSSettings",
    "AzureBlobStorageSettings",
    "AzureDocIntelligenceSettings",
    "AzureAIFoundrySettings",
    "AzureSettings",
    "Environment",
    "get_settings",
]
