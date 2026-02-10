from sqlalchemy.orm import Session

from ..models import Case
from .base import BaseRepository


class CaseRepository(BaseRepository[Case]):
    """Repository for Case operations."""

    def __init__(self, session: Session):
        super().__init__(Case, session)

    def get_by_urn(self, urn: str) -> Case | None:
        """Get case by URN."""
        return self.get_one_by(urn=urn)
