from functools import lru_cache
from loguru import logger

from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)


@lru_cache(maxsize=1)
def get_credentials() -> DefaultAzureCredential:
    """Get or create a cached DefaultAzureCredential instance.

    Uses LRU cache to avoid recreating credentials on every call.
    Enables CLI and managed identity authentication, suitable for both
    local development and Azure-hosted environments.
    """
    logger.debug("Initializing Azure DefaultAzureCredential")
    # Auth: running in Azure host; using DefaultAzureCredential without interactive sources.
    return DefaultAzureCredential(
        exclude_cli_credential=False,  # allow CLI auth
        exclude_managed_identity_credential=False,  # allow MSI auth
        exclude_interactive_browser_credential=True,
        exclude_visual_studio_code_credential=True,
        exclude_shared_token_cache_credential=True,
        exclude_environment_credential=True,
        exclude_powershell_credential=True,
        exclude_developer_cli_credential=True,
    )

def get_token_provider(scopes: str):
    """Get the token provider."""
    credential = get_credentials()
    return get_bearer_token_provider(credential, scopes)
