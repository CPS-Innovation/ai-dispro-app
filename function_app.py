import json

import azure.functions as func
from loguru import logger

from src.api import (
    health as health_handler,
    ingestion as ingestion_handler,
    analysis as analysis_handler,
    workflow as workflow_handler,
)


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="ping")
@app.route(route="ping", methods=[func.HttpMethod.GET])
async def ping(req: func.HttpRequest) -> func.HttpResponse:
    """Ping endpoint."""
    logger.info("HTTP trigger: ping")
    return func.HttpResponse("pong", status_code=200)


@app.function_name(name="health")
@app.route(route="health", methods=[func.HttpMethod.GET])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check."""
    logger.info("HTTP trigger: health")
    
    response = await health_handler(route=req.params.get("route", None))
    if response["status"] == "success":
        return func.HttpResponse(
            json.dumps(response),
            status_code=200
        )

    return func.HttpResponse(
        json.dumps(response),
        status_code=500
    )


@app.function_name(name="ingestion")
@app.route(route="ingestion", methods=[func.HttpMethod.POST])
async def ingestion(req: func.HttpRequest) -> func.HttpResponse:
    """Ingestion trigger."""
    logger.info("HTTP trigger: ingestion")

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Invalid JSON body"}),
            status_code=400
        )

    trigger_type = req_body.get("trigger_type", 'urn')
    value = req_body.get("value")
    experiment_id = req_body.get("experiment_id", None)
    correlation_id = req_body.get("correlation_id", None)

    if not trigger_type or not value:
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Missing required parameters, trigger_type and value are required",
            }),
            status_code=400
        )

    response = await ingestion_handler(
        trigger_type=trigger_type,
        value=value,
        experiment_id=experiment_id,
        correlation_id=correlation_id,
    )

    return func.HttpResponse(
        json.dumps(response),
        status_code=200 if response.get("status") == "success" else 500
    )


@app.function_name(name="analysis")
@app.route(route="analysis", methods=[func.HttpMethod.POST])
async def analysis(req: func.HttpRequest) -> func.HttpResponse:
    """Analysis trigger."""
    logger.info("HTTP trigger: analysis")

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Invalid JSON body"}),
            status_code=400
        )

    section_id = req_body.get("section_id", None)
    task_ids = req_body.get("task_ids", None)
    correlation_id = req_body.get("correlation_id", None)

    if section_id is None:
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Missing required parameters, section_id is required",
            }),
            status_code=400
        )

    response = await analysis_handler(
        section_id=section_id,
        task_ids=task_ids,
        correlation_id=correlation_id,
    )

    return func.HttpResponse(
        json.dumps(response),
        status_code=200 if response.get("status") == "success" else 500
    )


@app.function_name(name="workflow")
@app.route(route="workflow", methods=[func.HttpMethod.POST])
async def workflow(req: func.HttpRequest) -> func.HttpResponse:
    """Workflow trigger."""
    logger.info("HTTP trigger: workflow")

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Invalid JSON body"}),
            status_code=400
        )

    trigger_type = req_body.get("trigger_type")
    value = req_body.get("value")
    experiment_id = req_body.get("experiment_id", None)
    task_ids = req_body.get("task_ids", None)
    correlation_id = req_body.get("correlation_id", None)

    if not trigger_type or not value:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Missing required parameters"}),
            status_code=400
        )

    response = await workflow_handler(
        trigger_type=trigger_type,
        value=value,
        experiment_id=experiment_id,
        task_ids=task_ids,
        correlation_id=correlation_id,
    )

    return func.HttpResponse(
        json.dumps(response),
        status_code=200 if response.get("status") == "success" else 500
    )
