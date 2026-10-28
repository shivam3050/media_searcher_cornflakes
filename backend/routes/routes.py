from fastapi import APIRouter

from controllers.controllers import (
    login_user,
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

# Auth
router.add_api_route("/v1/login", login_user, methods=["POST"])

# Public
router.add_api_route("/v1/search", search_records, methods=["POST"])
router.add_api_route("/v1/similar/{id}", get_similar_records, methods=["GET"])

# Admin, simple
router.add_api_route("/v1/takedown", handle_takedown, methods=["POST"])
router.add_api_route("/v1/sources/{slug}/{action}", manage_source_action, methods=["POST"])
router.add_api_route("/v1/index/switch", switch_index_version, methods=["POST"])
router.add_api_route("/v1/ingest/{slug}", get_ingest_status, methods=["GET"])

# Admin, heavy (queue a job, worker.py does the work)
router.add_api_route("/v1/ingest/{slug}/run", trigger_ingest_run, methods=["POST"], status_code=202)
router.add_api_route("/v1/index/reembed", trigger_reembed, methods=["POST"], status_code=202)

# Internal
router.add_api_route("/metrics", get_system_metrics, methods=["GET"])