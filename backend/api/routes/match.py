from flask import json, make_response

from backend.db.queries.match import query_profile_matches, query_unreconciled_matches
from backend.utils.log import get_logger

logger = get_logger(__name__)


def get_unreconciled_matches(region_id):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": query_unreconciled_matches(region_id),
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown getting unreconciled matches."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


def get_profile_matches(region_id, profile_id):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": query_profile_matches(region_id, profile_id),
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown getting profile matches."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)
