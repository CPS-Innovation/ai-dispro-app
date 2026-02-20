from typing import Literal

import dotenv

from ..ingestion import IngestionOrchestrator, IngestionResult, TriggerType
from ..database import init_session_manager, init_database
from ..repositories import EventRepository

dotenv.load_dotenv()


async def ingestion(
    trigger_type: Literal[TriggerType.BLOB_NAME, TriggerType.FILEPATH, TriggerType.URN, TriggerType.URN_LIST],
    value: str,
    experiment_id: str | None = None,
    correlation_id: str | None = None,
):
    """Handle ingestion requests."""

    # Initialize database connection
    session_manager = init_session_manager()
    init_database()

    event_repo = EventRepository(session_manager.get_session())

    # Perform ingestion
    orchestrator = IngestionOrchestrator(
        event_repo=event_repo,
        correlation_id=correlation_id,
    )
    result: IngestionResult = await orchestrator.ingest(
        trigger_type=TriggerType(trigger_type),
        value=value,
        experiment_id=experiment_id,
    )

    return {
        "status": "success" if result.success else "error",
        "section_ids": result.section_ids,
        "experiment_id": experiment_id,
        "correlation_id": correlation_id,
        "error": result.error,
    }
