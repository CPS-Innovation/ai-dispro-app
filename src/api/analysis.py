import dotenv

from ..analysis import AnalysisOrchestrator, ExtractionResult
from ..models import AnalysisJob
from ..database import init_session_manager, init_database
from ..repositories import EventRepository

dotenv.load_dotenv()


async def analysis(
    section_ids: list[int] | None = None,
    version_ids: list[int] | None = None,
    task_ids: list[str] | None = None,
    experiment_id: str | None = None,
    correlation_id: str | None = None,
):
    """Extract/Analyze a content."""
    
    # Initialize database connection (idempotent setup)
    session_manager = init_session_manager()
    init_database()

    result = {
        'extraction': [],
        'analysis': [],
    } 
    with session_manager.session() as session:

        event_repo = EventRepository(session)

        # Perform analysis
        orchestrator = AnalysisOrchestrator(
            event_repo=event_repo,
            correlation_id=correlation_id,
        )


        section_ids = section_ids or []
        for version_id in version_ids or []:
            extraction_result: ExtractionResult = orchestrator.extract_section(
                version_id=version_id,
                experiment_id=experiment_id,
            )
            result['extraction'].append({
                "status": "success" if extraction_result.success else "error",
                "experiment_id": experiment_id,
                "version_id": version_id,
                "section_ids": extraction_result.section_ids,
                "correlation_id": correlation_id,
                "error": extraction_result.error,
            })
            section_ids.extend(extraction_result.section_ids)

        for section_id in section_ids:

            analysis_job: AnalysisJob = orchestrator.analyze_section(
                section_id=section_id,
                task_ids=task_ids,
            )
            result['analysis'].append({
                "experiment_id": analysis_job.experiment_id,
                "section_id": section_id,
                "analysis_job_id": analysis_job.id,
                "task_ids": analysis_job.task_ids if analysis_job.task_ids else [],
                "correlation_id": correlation_id,
            })
    
    return result