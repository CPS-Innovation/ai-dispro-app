import dotenv

from .ingestion import ingestion
from .analysis import analysis

dotenv.load_dotenv()


async def workflow(
    trigger_type: str,
    value: str | list[str],
    experiment_id: str | None = None,
    task_ids: list[str] | None = None,
    correlation_id: str | None = None,
):
    """Handle end-to-end ingestion and analysis workflow."""

    # Perform ingestion
    ingestion_result = await ingestion(
        trigger_type=trigger_type,
        value=value,
        experiment_id=experiment_id,
        correlation_id=correlation_id,
    )

    if ingestion_result.get('status') != "success":
        return {"ingestion": ingestion_result}

    version_ids = ingestion_result.get("version_ids", [])

    # Perform analysis on each ingested section
    analysis_results = await analysis(
        version_ids=version_ids,
        task_ids=task_ids,
        experiment_id=experiment_id,
        correlation_id=correlation_id,
    )

    return {
        "trigger_type": trigger_type,
        "value": value,
        "experiment_id": experiment_id,
        "correlation_id": correlation_id,
        "ingestion": ingestion_result,
        "analysis_results": analysis_results,
    }
