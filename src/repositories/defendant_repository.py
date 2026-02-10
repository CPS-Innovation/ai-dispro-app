from sqlalchemy.orm import Session

from ..models import Defendant
from .base import BaseRepository


class DefendantRepository(BaseRepository[Defendant]):
    """Repository for Defendant operations."""

    def __init__(self, session: Session):
        super().__init__(Defendant, session)
