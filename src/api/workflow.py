import dotenv

from ..database import init_session_manager, init_database
from .ingestion import ingestion
from .analysis import analysis

dotenv.load_dotenv()


async def workflow(
    trigger_type: str,
    value: str,
    experiment_id: str | None = None,
    task_ids: list[str] | None = None,
    correlation_id: str | None = None,
):
    """Handle end-to-end ingestion and analysis workflow."""

    # Initialize database connection
    init_session_manager()
    init_database()

    # Perform ingestion
    ingestion_result = await ingestion(
        trigger_type=trigger_type,
        value=value,
        experiment_id=experiment_id,
        correlation_id=correlation_id,
    )

    if ingestion_result.get('status') != "success":
        return ingestion_result

    section_ids = ingestion_result.get("section_ids", [])

    # Perform analysis on each ingested section
    analysis_results = []
    for section_id in section_ids:
        result = await analysis(
            section_id=section_id,
            task_ids=task_ids,
            correlation_id=correlation_id,
        )
        if result.get('status') != "success":
            return result
        analysis_results.append(result)

    return {
        "status": "success",
        "experiment_id": experiment_id,
        "correlation_id": correlation_id,
        "sections": section_ids,
        "analysis_job_ids": [res.get("analysis_job_id") for res in analysis_results],
    }
