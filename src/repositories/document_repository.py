from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document
from .base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document operations."""

    def __init__(self, session: Session):
        super().__init__(Document, session)

    def get_by_case(self, case_id: int) -> list[Document]:
        """Get all documents for a case."""
        stmt = select(Document).where(
            Document.case_id == case_id
        )
        return list(self.session.execute(stmt).scalars().all())
