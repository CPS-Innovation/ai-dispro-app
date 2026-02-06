from sqlalchemy.orm import Session

from ..models import Experiment
from .base import BaseRepository


class ExperimentRepository(BaseRepository[Experiment]):
    """Repository for Experiment operations."""

    def __init__(self, session: Session):
        super().__init__(Experiment, session)

    def get_by_id(self, id: str) -> Experiment | None:
        """Get experiment by ID."""
        return self.get_one_by(id=id)
