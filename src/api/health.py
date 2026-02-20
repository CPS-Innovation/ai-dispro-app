from typing import Literal

import dotenv
from loguru import logger
from sqlalchemy import inspect, text

from src.config import SettingsManager
from src.database.migrations import verify_schema

dotenv.load_dotenv()

async def health(
        route: Literal['blob', 'postgres', 'llm', 'docintel', 'cms'] | None = None,
    ) -> dict:
    """Health check function.

    Args:
        route (str): Specific route to check. Options are 'blob', 'postgres', 'llm', 'docintel', 'cms'.

    Returns:
        dict: Health status information.
    """
    logger.info("Health check invoked")

    # Validate settings
    settings = SettingsManager.get_instance()
    errors = settings.validate()
    if errors:
        logger.error(f"Settings validation errors: {errors}")
        return {"status": "error", "errors": errors}

    if route is None:
        logger.info("No specific route provided, returning overall readiness")
        return {"status": "success"}

    route_normalised = route.strip().lower()
    logger.info(f"Health check route: {route_normalised}")

    if route_normalised == "blob":
        # Test blob connection
        try:
            from src.services import get_blob_service_client
            client = get_blob_service_client(settings)
            containers = client.list_containers()
            containers = list(containers)
            logger.info(f"Blob connection successful, found {len(containers)} containers")
            return {"status": "success", "blob": f"connected ({len(containers)} containers)"}
        except Exception as e:
            logger.error(f"Blob connection failed: {e}")
            return {"status": "error", "blob": "disconnected", "error": str(e)}

    if route_normalised == "postgres":
        # Test database connection
        try:
            from src.database import init_session_manager
            from src.database.session import get_session_manager
            init_session_manager()
            session_manager = get_session_manager()
            inspector = inspect(session_manager.engine)
            existing_tables = set(inspector.get_table_names())
            logger.info(f"Database connection successful, found {len(existing_tables)} tables")
            with session_manager.session() as session:
                session.execute(text("SELECT 1"))
            verification = verify_schema(session_manager)
            return {"status": "success", "postgres": f"connected (verification {verification['status']}, {len(existing_tables)} tables)"}
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return {"status": "error", "postgres": "disconnected", "error": str(e)}

    if route_normalised == "llm":
        # Test LLM connection
        try:
            from src.services import get_llm_client
            client = get_llm_client(settings)
            logger.info("Client: %s", client)
            response = client.chat.completions.create(
                model=settings.ai_foundry.deployment_name,
                messages=[{"role": "user", "content": "1 + two + tree = ? Be concise."}],
                temperature=0.0,
            )
            answer = response.choices[-1].message.content
            return {"status": "success", "llm": f"connected ('{answer}')"}
        except Exception as e:
            logger.error(f"LLM connection failed: {e}")
            return {"status": "error", "llm": "disconnected", "error": str(e)}

    if route_normalised == "docintel":
        # Test Document Intelligence connection
        try:
            from pathlib import Path
            filepath =  Path(__file__).parent.parent.parent / "tests" / "test.pdf"
            logger.info(f"Filepath: {filepath}")
            
            with Path(filepath).open("rb") as fp:
                doc_bytes = fp.read()
                
                from src.services import get_docintel_client
                client = get_docintel_client(settings)
                # Create the AnalyzeDocumentRequest
                poller = client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    analyze_request=doc_bytes,
                    content_type="application/octet-stream",
                )
                result = poller.result()
                logger.info(f"Document Intelligence connection successful, result: {result}")
                return {"status": "success", "docintel": f"connected (pages: {len(result.pages)})"}
        except Exception as e:
            logger.error(f"Document Intelligence connection failed: {e}")
            return {"status": "error", "docintel": "disconnected", "error": str(e)}
    
    if route_normalised == "keyvault":
        # Test Key Vault connection
        try:
            from src.services import get_secret
            secret_name = settings.cms.username_secret_name
            get_secret(secret_name)
            logger.info(f"Key Vault connection successful, retrieved secret: {secret_name}")
            return {"status": "success", "keyvault": f"connected (secret name: {secret_name})"}
        except Exception as e:
            logger.error(f"Key Vault connection failed: {e}")
            return {"status": "error", "keyvault": "disconnected", "error": str(e)}
    
    if route_normalised == "cms":
        # Test CMS connection
        from src.services.cms_client import CMSClient
        client = CMSClient()
        urn = settings.test.cms_urn
        if not client.authenticate():
             logger.error("Failed to authenticate.")
             return {"status": "error", "cms": "disconnected", "error": "authentication failed"}
        case_id = client.get_case_id_from_urn(urn)
        if not case_id:
             logger.error("Failed to get case ID.")
             return {"status": "error", "cms": "disconnected", "error": "failed to get case ID"}

        return {"status": "success", "cms": f"connected (case_id length {len(str(case_id))})"}

    logger.warning(f"Unknown health check route: {route_normalised}")
    return {"status": "error", "error": f"Unknown route: {route_normalised}"}