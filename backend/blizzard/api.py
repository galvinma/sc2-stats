"""
https://develop.battle.net/documentation/starcraft-2/game-data-apis
https://develop.battle.net/documentation/starcraft-2/community-apis
"""

import time
from datetime import datetime, timedelta
from functools import wraps

import requests
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from backend.api.methods import SC2StatsAPI
from backend.db.db import query
from backend.db.model import BlizzardRequest
from backend.enums import RegionId
from backend.static import (
    BLIZZARD_API_BASE,
    BLIZZARD_CLIENT_ID,
    BLIZZARD_CLIENT_SECRET,
    BLIZZARD_OATH_BASE,
    REQUEST_MAX_PER_DAY,
    REQUEST_MAX_PER_SECOND,
)
from backend.utils.datetime import current_epoch_time, datetime_to_epoch
from backend.utils.log import get_logger

logger = get_logger(__name__)


class BlizzardAPIState:
    @classmethod
    def get_request_count(cls, region_id, timestamp):
        return query(
            params={BlizzardRequest},
            filters=[(BlizzardRequest.timestamp >= timestamp), (BlizzardRequest.region_id == region_id)],
            count=True,
        )

    @classmethod
    def get_second_request_count(cls, region_id):
        timestamp = datetime_to_epoch(datetime.now() - timedelta(0, 1))
        return BlizzardAPIState.get_request_count(region_id, timestamp)

    @classmethod
    def get_day_request_count(cls, region_id):
        timestamp = datetime_to_epoch(datetime.now() - timedelta(0, 86400))
        return BlizzardAPIState.get_request_count(region_id, timestamp)

    @classmethod
    def exceeded_max_requests(cls, region_id):
        second_request_count = BlizzardAPIState.get_second_request_count(region_id)
        day_request_count = BlizzardAPIState.get_day_request_count(region_id)
        exceeded = second_request_count >= REQUEST_MAX_PER_SECOND or day_request_count >= REQUEST_MAX_PER_DAY
        if exceeded:
            logger.debug(f"Exceeded max API requests. {region_id=}, {second_request_count=}, {day_request_count=}")
        return exceeded


class BlizzardApi:
    oauth_token = None
    oauth_token_expiration = None

    def _refesh_battlenet_oauth_token(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                if not BlizzardApi.oauth_token or BlizzardApi.token_expired():
                    endpoint = BLIZZARD_OATH_BASE + "/token"
                    params = {"grant_type": "client_credentials"}
                    res = requests.post(
                        url=endpoint, params=params, auth=(BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET)
                    ).json()
                    BlizzardApi.oauth_token = res["access_token"]
                    BlizzardApi.oauth_token_expiration = datetime.now() + timedelta(0, int(res["expires_in"]))
            except Exception:
                logger.exception("Exception thrown while POSTing for oauth token...")

            return func(*args, **kwargs)

        return _wrapper

    def token_expired():
        if not BlizzardApi.oauth_token_expiration:
            return True

        return datetime.now() > BlizzardApi.oauth_token_expiration

    def blizzard_headers():
        if not BlizzardApi.oauth_token:
            return {}

        return {"Authorization": f"Bearer {BlizzardApi.oauth_token}"}

    def block_request(self, region_id, url, interval=0.25):
        blocked = True
        while blocked:
            res = SC2StatsAPI.get(endpoint=f"/request/limit/{region_id}")
            blocked = res.get("blocked")
            if blocked:
                time.sleep(interval)

        SC2StatsAPI.post(
            endpoint="/post/blizzard_request",
            data={"url": url, "region_id": region_id, "timestamp": current_epoch_time()},
        )

    @_refesh_battlenet_oauth_token
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(0.1),
    )
    def _get(self, url, timeout):
        logger.info(f"Sending GET request to {url=}")

        try:
            res = requests.get(url, headers=BlizzardApi.blizzard_headers(), timeout=timeout)
        except requests.exceptions.Timeout:
            logger.error(f"Exceeded timeout fetching {url=}")
            return {}

        if res.ok:
            return res.json()

        if res.status_code == 503:
            logger.error(f"Service Unavailable. {res.status_code=}, {url=}")
            return {}

        if res.status_code == 429:
            logger.warning(f"Too May Requests. {res.status_code=}. Will retry...")
            raise Exception

        if res.status_code == 404:
            logger.error(f"Not found. {res.status_code=}, {url=}")
            return {}

        if res.status_code >= 400:
            logger.error(f"Failed GET. {res.status_code=}, {res.reason=}, {url=}. Will retry...")
            raise Exception

        return {}

    def get(self, region_id, url, timeout=10):
        try:
            self.block_request(region_id=region_id, url=url)
            return self._get(url=url, timeout=timeout)
        except RetryError:
            logger.exception(f"Exceeded retries fetching {url=}")
            return {}
        except Exception:
            logger.exception("Exception thrown in GET request.")
            return {}

    # Game Data API

    def get_league(self, region_id, season_id, queue_id, team_type, league_id):
        """
        /data/sc2/league/{seasonId}/{queueId}/{teamType}/{leagueId}
        """
        return self.get(
            region_id=region_id,
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/data/sc2/league/{season_id}/{queue_id}/{team_type}/{league_id}",
        )

    # Profile API

    def get_profile_ladder(self, region_id, realm_id, profile_id, ladder_id):
        """
        /sc2/profile/:regionId/:realmId/:profileId/ladder/:ladderId
        """
        return self.get(
            region_id=region_id,
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/profile/{region_id}/{realm_id}/{profile_id}/ladder/{ladder_id}",
            timeout=3,
        )

    # Ladder API

    def get_ladder_season(self, region_id):
        """
        /sc2/ladder/season/:regionId
        """
        return self.get(
            region_id=region_id,
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower()) + f"/sc2/ladder/season/{region_id}",
        )

    # Legacy API

    def get_legacy_ladder(self, region_id, ladder_id):
        """
        /sc2/legacy/ladder/:regionId/:ladderId
        """
        return self.get(
            region_id=region_id,
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/legacy/ladder/{region_id}/{ladder_id}",
        )

    def get_legacy_match_history(self, region_id, realm_id, profile_id):
        """
        /sc2/legacy/profile/:regionId/:realmId/:profileId/matches
        """
        return self.get(
            region_id=region_id,
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/legacy/profile/{region_id}/{realm_id}/{profile_id}/matches",
        )
