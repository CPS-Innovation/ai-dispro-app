from sqlalchemy.orm import Session

from ..models import Section
from .base import BaseRepository


class SectionRepository(BaseRepository[Section]):
    """Repository for Section operations."""

    def __init__(self, session: Session):
        super().__init__(Section, session)

    def get_by_document(self, document_id: int) -> list[Section]:
        """Get all sections for a document (across all versions)."""
        return self.get_by(document_id=document_id)
