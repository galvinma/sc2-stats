from flask import Flask, json, make_response, request

from backend.api.routes.match import get_profile_matches, get_unreconciled_matches
from backend.blizzard.api import BlizzardAPIState
from backend.db.db import (
    bulk_delete,
    bulk_insert,
    bulk_upsert,
    insert_stmt,
    query,
    query_in,
)
from backend.db.model import table_name_to_constraint, table_name_to_model
from backend.db.query import (
    query_character,
    query_ladder_character_mmrs,
    query_ladder_members,
    query_ladders,
    query_most_recent_etl_execution,
)
from backend.utils.log import get_logger

app = Flask(__name__)


logger = get_logger(__name__)


app.add_url_rule("/match/unreconciled/<region_id>/", methods=["GET"], view_func=get_unreconciled_matches)
app.add_url_rule("/match/profile/<region_id>/<profile_id>", methods=["GET"], view_func=get_profile_matches)


@app.route("/get/<table_name>", methods=["GET"])
def get(table_name):
    try:
        params = request.args.to_dict()
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": [
                        obj.as_dict() for obj in query(params={table_name_to_model(table_name)}, filter_by=params)
                    ],
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown during GET."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


@app.route("/post/<table_name>", methods=["POST"])
def post(table_name):
    try:
        data = request.get_json()
        rows = data["rows"] if "rows" in data else [data]
        stmt = insert_stmt(model=table_name_to_model(table_name), values=rows)
        bulk_insert(stmt=stmt, constraint=table_name_to_constraint(table_name))
        return make_response(json.dumps({"message": "Success"}), 200)
    except Exception:
        msg = "Exception thrown during POST."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


@app.route("/put/<table_name>", methods=["PUT"])
def put(table_name):
    try:
        data = request.get_json()
        rows = data["rows"] if "rows" in data else [data]
        stmt = insert_stmt(model=table_name_to_model(table_name), values=rows)
        if "set_" in data:
            set_ = {k: stmt.excluded[k] for k in data["set_"]} if "set_" in data else {}
            bulk_upsert(stmt=stmt, constraint=table_name_to_constraint(table_name), set_=set_)
        else:
            bulk_insert(stmt=stmt, constraint=table_name_to_constraint(table_name))

        return make_response(json.dumps({"message": "Success"}), 200)
    except Exception:
        msg = "Exception thrown during PUT."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


@app.route("/in/<table_name>/<column_name>", methods=["POST"])
def post_in(table_name, column_name):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": [
                        obj.as_dict()
                        for obj in query_in(
                            table_name_to_model(table_name), column_name, request.get_json().get("iterable")
                        )
                    ],
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown during POST/IN."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


@app.route("/in/<table_name>/<column_name>", methods=["DELETE"])
def delete_in(table_name, column_name):
    try:
        bulk_delete(table_name_to_model(table_name), column_name, request.get_json().get("iterable"))
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown during DELETE/IN."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


# Blizzard Request


@app.route("/request/limit/<region_id>", methods=["GET"])
def get_request_limit(region_id):
    """Return if application has exceeded request limit for given region"""
    try:
        return make_response(json.dumps({"blocked": BlizzardAPIState.exceeded_max_requests(region_id)}), 200)
    except Exception:
        msg = "Exception thrown while determining API request limit."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


# ETL


@app.route("/latest_etl_execution/<name>/<region_id>", methods=["GET"])
def get_most_recent_etl_execution(name, region_id):
    """Return most recent ETL execution for given name and region_id"""
    try:
        return make_response(json.dumps(query_most_recent_etl_execution(name, region_id)), 200)
    except Exception:
        msg = "Exception thrown while getting recent ETL execution."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


# Ladder


@app.route("/ladder/<season_id>/<region_id>", methods=["GET"])
def get_ladders(season_id, region_id):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": query_ladders(season_id=season_id, region_id=region_id),
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown while fetching ladders."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


@app.route("/ladder_member/<ladder_id>", methods=["GET"])
def get_ladder_members(ladder_id):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": query_ladder_members(ladder_id=ladder_id),
                },
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown while fetching ladder members."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


@app.route("/ladder/character_mmr/<pkey_ladder_id>", methods=["GET"])
def get_ladder_character_mmrs(pkey_ladder_id):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": query_ladder_character_mmrs(pkey_ladder_id=pkey_ladder_id),
                },
                default=str,
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown while fetching character_mmrs for given ladder."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


# Character


@app.route("/character/<region_id>/<realm_id>/<profile_id>/<display_name>", methods=["GET"])
def get_character(region_id, realm_id, profile_id, display_name):
    try:
        return make_response(
            json.dumps(
                {
                    "message": "Success",
                    "results": query_character(region_id, realm_id, profile_id, display_name),
                }
            ),
            200,
        )
    except Exception:
        msg = "Exception thrown while fetching character."
        logger.exception(msg)
        return make_response(json.dumps({"message": msg}), 500)


# Match
