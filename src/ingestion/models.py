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
    case_ids: list[int] | None = None
    document_ids: list[int] | None = None
    version_ids: list[int] | None = None
    error: str | None = None
    
    def __post_init__(self):
        if self.document_ids is None:
            self.document_ids = []
        if self.version_ids is None:
            self.version_ids = []
        if self.case_ids is None:
            self.case_ids = []