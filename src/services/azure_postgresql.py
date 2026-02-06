from ..config import SettingsManager
from .azure_identity import get_credentials

AZURE_PG_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


def get_connection_string(settings: SettingsManager | None = None) -> str:
    """Get PostgreSQL connection string with specified schema."""

    database = (settings or SettingsManager.get_instance()).database
    credential = get_credentials()
    password = credential.get_token(AZURE_PG_SCOPE).token

    return (   
        f"postgresql+psycopg2://{database.username}:{password}"
        f"@{database.host}:{database.port}/{database.name}"
        f"?options=-c%20search_path%3D{database.schema}" # psycopg2 URL-encoded
        "&sslmode=require" # Azure requires SSL
    )
