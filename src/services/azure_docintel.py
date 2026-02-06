from azure.ai.documentintelligence import DocumentIntelligenceClient

from ..config import SettingsManager
from . import get_credentials


def get_docintel_client(
        settings: SettingsManager | None = None
    ) -> DocumentIntelligenceClient:
    """Initialise the client."""
    settings = settings or SettingsManager.get_instance()
    credential = get_credentials()
    return DocumentIntelligenceClient(
        endpoint=settings.doc_intelligence.endpoint,
        credential=credential,
        api_version=settings.doc_intelligence.api_version,
    )
