from sqlalchemy.orm import Session

from ..models import Offence
from .base import BaseRepository


class OffenceRepository(BaseRepository[Offence]):
    """Repository for Offence operations."""

    def __init__(self, session: Session):
        super().__init__(Offence, session)
