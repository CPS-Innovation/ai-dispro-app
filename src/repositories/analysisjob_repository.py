from sqlalchemy.orm import Session

from ..models import AnalysisJob
from .base import BaseRepository


class AnalysisJobRepository(BaseRepository[AnalysisJob]):
    """Repository for AnalysisJob operations."""

    def __init__(self, session: Session):
        super().__init__(AnalysisJob, session)
