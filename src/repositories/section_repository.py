from sqlalchemy.orm import Session

from ..models import Section
from .base import BaseRepository


class SectionRepository(BaseRepository[Section]):
    """Repository for Section operations."""

    def __init__(self, session: Session):
        super().__init__(Section, session)
