import dotenv

from ..analysis import AnalysisOrchestrator
from ..models import AnalysisJob
from ..database import init_session_manager, init_database
from ..repositories import EventRepository

dotenv.load_dotenv()


async def analysis(
    section_id: str,
    task_ids: list[str] | None = None,
    correlation_id: str | None = None,
):
    """Analyze a content section."""
    
    # Initialize database connection
    session_manager = init_session_manager()
    init_database()

    event_repo = EventRepository(session_manager.get_session())

    # Perform analysis
    orchestrator = AnalysisOrchestrator(
        event_repo=event_repo,
        correlation_id=correlation_id,
    )
    analysis_job: AnalysisJob = orchestrator.analyze_section(
        section_id=section_id,
        task_ids=task_ids,
    )

    return {
        "status": "success",
        "experiment_id": analysis_job.experiment_id,
        "section_id": section_id,
        "analysis_job_id": analysis_job.id,
        "task_ids": analysis_job.task_ids,
        "correlation_id": correlation_id,
    }
