from loguru import logger

from ..base_worker import AnalysisWorker
from ...models import AnalysisResult


class EchoWorker(AnalysisWorker):
    """Worker that returns a static content."""

    def analyze(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
    ) -> list[AnalysisResult]:
        """Execute analysis on section content."""
        logger.info(f"Analyzing section {section_id} for experiment {experiment_id}")
        
        # Create AnalysisResult instances
        results = [
            AnalysisResult(
                analysis_job_id=analysis_job_id,
                experiment_id=experiment_id,
                prompt_template_id=None,
                content=self.config.get("content", None),
                justification=self.config.get("justification", None),
                self_confidence=float(self.config.get("self_confidence", None)),
            ) for _ in range(1)  # Example: create one result
        ]
        
        logger.info(f"Found {len(results)} results for section {section_id}")
        
        if self.save_results:
            self.save_results_to_db(results)

        return results
