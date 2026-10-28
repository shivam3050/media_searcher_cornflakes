from fastapi import APIRouter, HTTPException

from ..controllers.controllers import (
    search_records,
    get_similar_records,
    handle_takedown,
    manage_source_action,
    trigger_ingest_run,
    get_ingest_status,
    trigger_reembed,
    switch_index_version,
    get_system_metrics,
)


router = APIRouter()

# Search & Similarity Endpoints

@router.add_api_route("/v1/search", search_records, methods=["POST"])
@router.add_api_route("/v1/similar/{id}", get_similar_records, methods=["GET"])

# Moderation & Source Management Endpoints
@router.add_api_route("/v1/takedown", handle_takedown, methods=["POST"])
@router.add_api_route("/v1/sources/{slug}/{action}", manage_source_action, methods=["POST"])

# Data Ingestion Pipeline Endpoints
@router.add_api_route("/v1/ingest/{slug}/run", trigger_ingest_run, methods=["POST"], status_code=202)
@router.add_api_route("/v1/ingest/{slug}", get_ingest_status, methods=["GET"])

# Vector Indexing & Version Management Endpoints
@router.add_api_route("/v1/index/reembed", trigger_reembed, methods=["POST"], status_code=202)
@router.add_api_route("/v1/index/switch", switch_index_version, methods=["POST"])

# System Monitoring Endpoint
@router.add_api_route("/metrics", get_system_metrics, methods=["GET"])


