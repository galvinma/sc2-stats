"""
https://develop.battle.net/documentation/starcraft-2/game-data-apis
https://develop.battle.net/documentation/starcraft-2/community-apis
"""

import time
from datetime import datetime, timedelta
from functools import wraps
from threading import Lock

import requests
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from backend.db.db import ENGINE, create, query, session_scope
from backend.db.model import Request
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


class APIState:

    lock = Lock()

    @classmethod
    def get_request_count(cls, timestamp):
        with session_scope(engine=ENGINE) as session:
            count = query(session, params={Request}, filters=[(Request.timestamp >= timestamp)], count=True)
            return count

    @classmethod
    def get_second_request_count(cls):
        lookback = datetime_to_epoch(datetime.now() - timedelta(0, 1))
        return APIState.get_request_count(lookback)

    @classmethod
    def get_day_request_count(cls):
        lookback = datetime_to_epoch(datetime.now() - timedelta(0, 86400))
        return APIState.get_request_count(lookback)

    @classmethod
    def exceeded_max_requests(cls):
        second_request_count = APIState.get_second_request_count()
        day_request_count = APIState.get_day_request_count()
        exceeded = second_request_count >= REQUEST_MAX_PER_SECOND or day_request_count >= REQUEST_MAX_PER_DAY
        if exceeded:
            logger.info(f"Exceeded max API requests. {second_request_count=}, {day_request_count=}")
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

    def headers():
        if not BlizzardApi.oauth_token:
            return {}

        return {"Authorization": f"Bearer {BlizzardApi.oauth_token}"}

    def block_request(self, url, interval=0.25):
        blocked = True
        while blocked:
            with APIState.lock:
                blocked = APIState.exceeded_max_requests()

            if blocked:
                time.sleep(interval)

        with session_scope(engine=ENGINE) as session:
            create(session=session, instance=Request(url=url, timestamp=current_epoch_time()))

    @_refesh_battlenet_oauth_token
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(0.25),
    )
    def _get(self, url):
        logger.info(f"Sending GET request to {url=}")
        res = requests.get(url, headers=BlizzardApi.headers())
        if res.ok:
            return res.json()

        if res.status_code == 503:
            logger.error(f"Service Unavailable. {res.status_code=}, {url=}. Will retry...")
            raise Exception

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

    def get(self, url):
        try:
            self.block_request(url=url)
            return self._get(url=url)
        except RetryError:
            logger.error(f"Exceeded retries fetching {url=}")
            return {}

    # Game Data API

    def get_league(self, region_id, season_id, queue_id, team_type, league_id):
        """
        /data/sc2/league/{seasonId}/{queueId}/{teamType}/{leagueId}
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/data/sc2/league/{season_id}/{queue_id}/{team_type}/{league_id}"
        )

    # Profile API

    def get_profile_ladder(self, region_id, realm_id, profile_id, ladder_id):
        """
        /sc2/profile/:regionId/:realmId/:profileId/ladder/:ladderId
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/profile/{region_id}/{realm_id}/{profile_id}/ladder/{ladder_id}"
        )

    # Ladder API

    def get_ladder_season(self, region_id):
        """
        /sc2/ladder/season/:regionId
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower()) + f"/sc2/ladder/season/{region_id}"
        )

    # Legacy API

    def get_legacy_ladder(self, region_id, ladder_id):
        """
        /sc2/legacy/ladder/:regionId/:ladderId
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/legacy/ladder/{region_id}/{ladder_id}"
        )

    def get_legacy_match_history(self, region_id, realm_id, profile_id):
        """
        /sc2/legacy/profile/:regionId/:realmId/:profileId/matches
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/legacy/profile/{region_id}/{realm_id}/{profile_id}/matches"
        )
