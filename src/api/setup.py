import json
from pathlib import Path

import dotenv
from loguru import logger
from sqlalchemy import inspect, text

from ..config import SettingsManager
from ..services import save_blob
from ..database import (
    init_database,
    init_session_manager,
    SessionManager,
    verify_schema,
)

dotenv.load_dotenv()

async def setup(
        tables_to_drop: list[str] | None = None,
        tables_to_truncate: list[str] | None = None,
        grantee: str | None = None,
        tables_to_grant_permission: list[str] | None = None,
        sequences_to_grant_permission: list[str] | None = None,
        views_to_grant_permission: list[str] | None = None,
        create_views: bool = False,
        blob_test_upload: bool = False,
) -> dict:
    """Setup function to verify database schema and other initial checks."""
    logger.info("Setup invoked")
    settings = SettingsManager.get_instance()
    session_manager: SessionManager = init_session_manager()

    with session_manager.get_session() as session:
        # Truncate tables if specified
        for tbl_idx, tbl_name in enumerate(tables_to_truncate or []):
            sttmt = "TRUNCATE TABLE {tbl_name} RESTART IDENTITY CASCADE;".format(tbl_name=tbl_name)
            session.session.execute(text(sttmt))
            session.session.commit()
            logger.info(f"Truncated table {tbl_name} ({tbl_idx+1}/{len(tables_to_truncate)})")

        # Drop tables if specified
        for tbl_idx, tbl_name in enumerate(tables_to_drop or []):
            sttmt = "DROP TABLE {tbl_name} RESTART IDENTITY CASCADE;".format(tbl_name=tbl_name)
            session.execute(text(sttmt))
            session.commit()
            logger.info(f"Dropped table {tbl_name} ({tbl_idx+1}/{len(tables_to_drop)})")

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

    # Grant permissions on tables if specified
    for tlb_idx, tbl_name in enumerate(tables_to_grant_permission or []):
        session_manager.grant_access(
            object_type="TABLE",
            object_name=tbl_name,
            operations=[
                "SELECT",
                "INSERT",
                "UPDATE",
            ],
            grantee=grantee,
        )
        logger.info(f"Granted permission on table {tbl_name} to {grantee} ({tlb_idx+1}/{len(tables_to_grant_permission)})")

    # Grant permissions on sequences if specified
    for seq_idx, seq_name in enumerate(sequences_to_grant_permission or []):
        session_manager.grant_access(
            object_type="SEQUENCE",
            object_name=seq_name,
            operations=[
                "USAGE",
                "SELECT",
                "UPDATE",
            ],
            grantee=grantee,
        )
        logger.info(f"Granted permission on sequence {seq_name} to {grantee} ({seq_idx+1}/{len(sequences_to_grant_permission)})")

    # Grant permissions on views if specified
    for view_idx, view_name in enumerate(views_to_grant_permission or []):
        session_manager.grant_access(
            object_type="VIEW",
            object_name=view_name,
            operations=[
                "SELECT",
            ],
            grantee=grantee,
        )
        logger.info(f"Granted permission on view {view_name} to {grantee} ({view_idx+1}/{len(views_to_grant_permission)})")
    
    # Final schema verification
    verification = verify_schema(session_manager) # verify schema
    response = { "status": "success", "verification": verification }

    # Test blob upload if specified
    if blob_test_upload:
        filepaths = [
             Path(__file__).parent.parent.parent / "tests" / "test.pdf"
        ]
        for filepath in filepaths:
            with open(filepath, "rb") as file_data:
                save_blob(
                    container_name=settings.storage.blob_container_name_source,
                    blob_name=filepath,
                    data=file_data
                )
        response['blob_test_upload'] = "success"

    # Create views if specified
    if create_views:
        with session_manager.get_session() as session:
            for view_name, view_sql in VIEWS.items():
                session.execute(text(view_sql))
                session.commit()
                logger.info(f"Created view {view_name}")
        response['views_created'] = list(VIEWS.keys())

    return response


VIEWS = {
"documents_q4q3":
"""
CREATE OR REPLACE VIEW ai_dispro_schema.documents_q4q3 AS
SELECT 
    NULL AS partition_key,
    doc_.id AS row_key,
    NULL AS experiment_id,
    doc_.case_id AS case_id,
    doc_.original_file_name AS doc_name,
    case_.finalised AS status,
    charge_.latest_verdict AS decision,
    defendant_.ethnicity AS ethnicity,
    charge_.description AS crime,
    NULL AS is_police,
    NULL AS is_cps,
    doc_.created_at AS created_on
FROM ai_dispro_schema.documents_q4 doc_
INNER JOIN ai_dispro_schema.cases_q4 case_ ON case_.id = doc_.case_id
LEFT JOIN ai_dispro_schema.defendants_q4 defendant_ ON defendant_.id = (
 SELECT MIN(d.id)
 FROM ai_dispro_schema.defendants_q4 d
 WHERE d.case_id = case_.id
)
LEFT JOIN ai_dispro_schema.charges_q4 charge_ ON charge_.id = (
 SELECT MIN(c.id)
 FROM ai_dispro_schema.charges_q4 c
 WHERE c.defendant_id = defendant_.id
);
""",
"sections_q4q3":
"""
CREATE OR REPLACE VIEW ai_dispro_schema.sections_q4q3 AS
SELECT 
 section_.experiment_id as partition_key,
 section_.id as row_key,
 section_.experiment_id as experiment_id,
 section_.document_id as doc_id,
 section_.id as id,
 section_.id as subsection_id,
 section_.redacted_content as content,
 section_.created_at as created_on
FROM ai_dispro_schema.sections_q4 section_;
"""
,
"analyses_q4q3":
"""
CREATE OR REPLACE VIEW ai_dispro_schema.analyses_q4q3 AS
SELECT 
	results_.experiment_id as partition_key,
	results_.id as row_key,
	results_.id as analysis_id,
	section_.document_id as doc_id,
	section_.id as subsection_id,
	results_.experiment_id as experiement_id,
	results_.pattern_id as pattern_id,
	results_.category_id as category_id,
	prompts_.version as prompt_version,
	results_.content as "content",
	results_.justification as justification,
	results_.self_confidence as self_confidence,
	results_.created_at as created_on
FROM ai_dispro_schema.analysisresults_q4 results_
INNER JOIN ai_dispro_schema.analysisjobs_q4 jobs_ ON jobs_.id = results_.analysis_job_id
INNER JOIN ai_dispro_schema.sections_q4 section_ ON section_.id = jobs_.section_id
LEFT JOIN ai_dispro_schema.prompt_templates_q4 prompts_ on prompts_.id = CAST(results_.prompt_template_id AS INTEGER)
"""
}