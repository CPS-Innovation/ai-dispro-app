from sqlalchemy.orm import Session

from ..models.version import Version
from .base import BaseRepository


class VersionRepository(BaseRepository[Version]):
    """Repository for Version operations."""

    def __init__(self, session: Session):
        super().__init__(Version, session)
