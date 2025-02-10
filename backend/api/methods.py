import requests
from flask import json
from tenacity import retry, stop_after_attempt, wait_fixed

from backend.static import SC2_STATS_API_BASE, SC2_STATS_API_PORT
from backend.utils.log import get_logger

logger = get_logger(__name__)

# TODO Add auth
# TODO Add retry logic


class SC2StatsAPI:

    @classmethod
    def headers(cls):
        return {"Content-Type": "application/json"}

    @classmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(0.25))
    def get(cls, endpoint, params=None):
        logger.debug(f"Sending GET request to {endpoint=}")
        res = requests.get(
            SC2_STATS_API_BASE + ":" + SC2_STATS_API_PORT + endpoint, params=params, headers=SC2StatsAPI.headers()
        )
        return res.json()

    @classmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(0.25))
    def post(cls, endpoint, data):
        logger.debug(f"Sending POST request to {endpoint=}")
        res = requests.post(
            url=SC2_STATS_API_BASE + ":" + SC2_STATS_API_PORT + endpoint,
            headers=SC2StatsAPI.headers(),
            data=json.dumps(data, default=str),
        )
        return res.json()

    @classmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(0.25))
    def put(cls, endpoint, data):
        logger.debug(f"Sending PUT request to {endpoint=}")
        res = requests.put(
            url=SC2_STATS_API_BASE + ":" + SC2_STATS_API_PORT + endpoint,
            headers=SC2StatsAPI.headers(),
            json=data,
        )
        return res.json()

    @classmethod
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(0.25))
    def delete(cls, endpoint, data):
        logger.debug(f"Sending DELETE request to {endpoint=}")
        res = requests.delete(
            url=SC2_STATS_API_BASE + ":" + SC2_STATS_API_PORT + endpoint,
            headers=SC2StatsAPI.headers(),
            data=json.dumps(data, default=str),
        )
        return res.json()
