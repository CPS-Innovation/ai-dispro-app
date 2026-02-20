from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from ..models import AnalysisResult
from ..database import get_session
from ..repositories import AnalysisResultRepository


class AnalysisWorker(ABC):
    """Abstract base class for analysis workers."""

    config: dict[str, Any]
    save_results: bool

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        save_results: bool = True,
    ):
        """Initialize the worker."""
        self.config = config or {}
        self.save_results = save_results

    @abstractmethod
    def analyze(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
    ) -> list[AnalysisResult]:
        """Execute analysis on section content.
        
        Args:
            text: The text content to analyze
            experiment_id: The experiment ID
            section_id: The section ID
            analysis_job_id: The analysis job ID
            
        Returns:
            List of AnalysisResult instances
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def save_results_to_db(
        self,
        results: list[AnalysisResult] = [],
    ) -> None:
        """Persist analysis results to database.
        
        Args:
            results: List of AnalysisResult instances to save
        """
        with get_session() as session:
            repo = AnalysisResultRepository(session)
            try:
                for result in results:
                    repo.upsert(**result.to_dict())
                session.commit()
                logger.info(f"Saved {len(results)} results in {__name__}")
            except Exception as e:
                session.rollback()
                logger.error(f"Error saving results: {str(e)}")
                raise

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} config={self.config}>"
    
    def __str__(self) -> str:
        return self.__repr__()
