import json

import dotenv
from loguru import logger
from sqlalchemy import inspect, text
import re

from ..database import (
    init_database,
    init_session_manager,
    SessionManager,
    verify_schema,
)
from ..repositories import PromptTemplateRepository
from ..models import PromptTemplate


dotenv.load_dotenv()


async def setup(
        views: list[dict] | None = None,
        prompt_templates: list[dict] | None = None,
) -> dict:
    """Setup function to verify database schema and other initial checks."""
    logger.info("Setup invoked")
    session_manager: SessionManager = init_session_manager()

    # Verify schema before initialization (in case of missing tables, etc.)
    verification = verify_schema(session_manager) # verify schema
    if verification["status"] != "ok":
        logger.warning("Schema verification:", json.dumps(verification, indent=2))

    # Create missing tables (if any)
    logger.info("Creating missing tables... (if any)")
    init_database(session_manager) # create tables (if not exist)
    logger.info("Verifying schema after initialization...")
    verification = verify_schema(session_manager)
    if verification["status"] != "ok":
        logger.warning("Schema verification after init:", json.dumps(verification, indent=2))
    else:
        logger.info("Schema verification after init: OK")

    inspector = inspect(session_manager.engine)
    logger.info("Existing tables:\n" + "="*16)
    for t in list(inspector.get_table_names()):
        logger.info(t)

    # Final schema verification
    verification = verify_schema(session_manager) # verify schema
    response = { 
        "status": "success",
        "verification": verification,
    }

    # Create views if specified
    if views is not None:
        logger.info(f"Upserting {len(views)} views...")
        response['views'] = {"upserted": 0, "errors": []}
        with session_manager.get_session() as session:
            for idx, ddl in enumerate(views):
                validate_create_view_ddl(ddl)
                try:
                    session.execute(text(ddl))
                    session.commit()
                    logger.info(f"Upserted view {idx}: {ddl}")
                    response['views']['upserted'] += 1
                except Exception as e:
                    logger.error(f"Error Upserting view {idx}: {e}")
                    response['views']['errors'].append(f"View {idx}: {e}")

    # Upload prompt templates if specified
    if prompt_templates is not None:
        logger.info(f"Upserting {len(prompt_templates)} prompt templates...")
        response['prompt_templates'] = {"upserted": [], "error": []}
        with session_manager.get_session() as session:
            prompt_repo = PromptTemplateRepository(session)
            for idx, pt in enumerate(prompt_templates):
                try:
                    pt_obj: PromptTemplate = prompt_repo.upsert(**pt)
                    session.commit()
                    logger.info(f"Upserted prompt template {idx}: {pt_obj.id}")
                    response['prompt_templates']['upserted'].append(pt_obj.id)
                except Exception as e:
                    logger.error(f"Error Upserting prompt template {idx}: {e}")
                    response['prompt_templates']['errors'].append(pt.get('name', 'unknown') + ": " + str(e))

    return response


def validate_create_view_ddl(ddl: str) -> None:
    """Validate that the provided DDL is a single CREATE [OR REPLACE] VIEW statement."""
    # Strip single-line and multi-line comments before analysis
    cleaned = re.sub(r'--[^\n]*', '', ddl)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip().rstrip(';').strip()

    if ';' in cleaned:
        raise ValueError("Multiple statements detected in DDL")

    if not re.match(r'^CREATE\s+(OR\s+REPLACE\s+)?VIEW\s+', cleaned, re.IGNORECASE):
        raise ValueError("DDL must be a single CREATE [OR REPLACE] VIEW statement")
