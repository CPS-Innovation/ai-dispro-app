from sqlalchemy.orm import Session

from ..models import Defendant
from .base import BaseRepository


class DefendantRepository(BaseRepository[Defendant]):
    """Repository for Defendant operations."""

    def __init__(self, session: Session):
        super().__init__(Defendant, session)

    def get_by_case(self, urn: str, case_id: int) -> list[Defendant]:
        """Get all defendants for a case."""
        return self.get_by(urn=urn, case_id=case_id)
