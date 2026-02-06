from sqlalchemy.orm import Session

from ..models import AnalysisResult
from .base import BaseRepository


class AnalysisResultRepository(BaseRepository[AnalysisResult]):
    """Repository for AnalysisResult operations."""

    def __init__(self, session: Session):
        super().__init__(AnalysisResult, session)

    def get_by_job(self, analysis_job_id: str) -> list[AnalysisResult]:
        """Get all results for an analysis job."""
        return self.get_by(analysis_job_id=analysis_job_id)
