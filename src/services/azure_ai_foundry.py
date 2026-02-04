from openai import AzureOpenAI

from ..config import SettingsManager
from .azure_identity import get_token_provider

AZURE_AF_SCOPE = "https://cognitiveservices.azure.com/.default"


def get_llm_client(
    settings: SettingsManager | None = None
) -> AzureOpenAI:
    """Initialise the client."""
    ai_foundry = (settings or SettingsManager.get_instance()).ai_foundry
    token_provider = get_token_provider(scopes=AZURE_AF_SCOPE)

    return AzureOpenAI(
        azure_endpoint=ai_foundry.endpoint,
        azure_ad_token_provider=token_provider,
        api_version=ai_foundry.api_version,
    )
