from enum import Enum
from dataclasses import dataclass


class TriggerType(str, Enum):
    """Ingestion trigger types as defined in likec4."""
    URN = "urn"
    BLOB_NAME = "blob_name"
    FILEPATH = "filepath"


@dataclass
class IngestionResult:
    """Ingestion result with created entity IDs."""
    success: bool
    case_id: str | None = None
    document_ids: list[str] = None
    version_ids: list[str] = None
    section_ids: list[str] = None
    error: str | None = None
    
    def __post_init__(self):
        if self.document_ids is None:
            self.document_ids = []
        if self.version_ids is None:
            self.version_ids = []
        if self.section_ids is None:
            self.section_ids = []
