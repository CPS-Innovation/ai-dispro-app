from loguru import logger
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

from ..config import SettingsManager
from .azure_identity import get_credentials

def get_secret(secret_name: str, settings: SettingsManager | None = None) -> str:
    """Retrieve a secret from Azure Key Vault."""
    azure = (settings or SettingsManager.get_instance()).azure
    logger.debug("Retrieving secret from Key Vault: {}", secret_name)
    try:
        credential = get_credentials()
        secret_client = SecretClient(
            vault_url=azure.key_vault_url,
            credential=credential,
        )
        secret_value = secret_client.get_secret(secret_name).value
        logger.debug("Successfully retrieved secret: {}", secret_name)
        return secret_value
    except ResourceNotFoundError:
        logger.error("Secret not found in Key Vault: {}", secret_name)
        raise
    except ClientAuthenticationError as e:
        logger.error("Authentication failed when accessing Key Vault: {}", str(e))
        raise
