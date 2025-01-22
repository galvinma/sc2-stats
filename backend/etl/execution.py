from more_itertools import one

from backend.api.methods import SC2StatsAPI
from backend.db.model import ETLExecution
from backend.utils.datetime import current_epoch_time
from backend.utils.log import get_logger

logger = get_logger(__name__)


def initiate_etl_execution(name, region_id, start_timestamp=None):
    if start_timestamp is None:
        start_timestamp = current_epoch_time()

    data = {"name": name, "region_id": region_id, "start_timestamp": start_timestamp}
    SC2StatsAPI.post(
        endpoint="/post/etl_execution",
        data={"rows": [data]},
    )
    return ETLExecution(
        **one(
            SC2StatsAPI.get(endpoint="/get/etl_execution", params=data).get("results"),
        )
    )


def conclude_etl_execution(etl_execution, end_timestamp=None):
    if end_timestamp is None:
        end_timestamp = current_epoch_time()

    etl_execution.end_timestamp = end_timestamp
    etl_execution.duration = end_timestamp - etl_execution.start_timestamp
    SC2StatsAPI.put(
        endpoint="/put/etl_execution",
        data={"rows": [etl_execution.as_dict()], "set_": ["end_timestamp", "duration"]},
    )


def latest_etl_execution(name, region_id):
    latest = SC2StatsAPI.get(endpoint=f"/latest_etl_execution/{name}/{region_id}")
    return ETLExecution(**one(latest)) if latest else None
