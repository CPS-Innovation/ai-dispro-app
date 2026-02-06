from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import AnalysisJob
from .base import BaseRepository


class AnalysisJobRepository(BaseRepository[AnalysisJob]):
    """Repository for AnalysisJob operations."""

    def __init__(self, session: Session):
        super().__init__(AnalysisJob, session)

    def get_by_section(self, section_id: int) -> list[AnalysisJob]:
        """Get all analysis jobs for a section."""
        return self.get_by(section_id=section_id)

    def get_by_experiment(self, experiment_id: str) -> list[AnalysisJob]:
        """Get analysis jobs by experiment ID."""
        return self.get_by(experiment_id=experiment_id)

    def get_with_results(self, job_id: int) -> AnalysisJob | None:
        """Get analysis job with results eagerly loaded."""
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .options(joinedload(AnalysisJob.results))
        )
        return self.session.execute(stmt).scalar_one_or_none()
