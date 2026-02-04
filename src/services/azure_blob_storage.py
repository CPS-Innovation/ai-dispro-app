from loguru import logger
from azure.storage.blob import BlobServiceClient

from ..config import SettingsManager
from .azure_identity import get_credentials


def get_blob_service_client(
        settings: SettingsManager | None = None,
    ) -> BlobServiceClient:
    """Initialise the client."""
    blob_storage = (settings or SettingsManager.get_instance()).blob_storage
    credential = get_credentials()
    return BlobServiceClient(
        account_url=f"https://{blob_storage.account_name}.blob.core.windows.net",
        credential=credential,
    )


def load_blob(container_name: str, blob_name: str) -> bytes:
    """Load document from Azure Blob Storage."""
    logger.debug(
        "Loading blob. Container: {}, Blob: {}",
        container_name,
        blob_name,
    )
    
    with get_blob_service_client() as blob_service_client:
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )
        content = blob_client.download_blob().readall()
    
    return content


async def save_blob(
        container_name: str,
        blob_name: str,
        data: bytes,
    ) -> None:
    """Save document to Azure Blob Storage."""
    logger.debug(
        "Saving blob. Container: {}, Blob: {}",
        container_name,
        blob_name,
    )
    
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(container=container_name)
        if not container_client.exists():
            container_client.create_container()
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )
        blob_client.upload_blob(data, overwrite=True)
