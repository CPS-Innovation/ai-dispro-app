from dataclasses import dataclass

@dataclass
class ExtractionResult:
    """Extraction result with created entity IDs."""
    success: bool
    version_id: int | None = None
    section_ids: list[int] | None = None
    error: str | None = None
    
    def __post_init__(self):
        if self.section_ids is None:
            self.section_ids = []
