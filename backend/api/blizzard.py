"""
https://develop.battle.net/documentation/starcraft-2/game-data-apis
https://develop.battle.net/documentation/starcraft-2/community-apis
"""

import logging
from datetime import datetime, timedelta
from functools import wraps

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from backend.enums import RegionId
from backend.static import (
    BLIZZARD_API_BASE,
    BLIZZARD_CLIENT_ID,
    BLIZZARD_CLIENT_SECRET,
    BLIZZARD_OATH_BASE,
)


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
                logging.exception("Exception thrown while POSTing for oauth token...")

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

    @_refesh_battlenet_oauth_token
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get(self, url):
        logging.info(f"Sending GET request to {url=}")
        res = requests.get(url, headers=BlizzardApi.headers())
        if res.ok:
            return res.json()

        if res.status_code == 503:
            logging.error(f"Service Unavailable. {res.status_code=}, {res.reason=}, {url=}")
            return {}

        if res.status_code == 429:
            logging.warning("Too May Requests. Will wait and retry...")
            raise Exception

        if res.status_code == 404:
            logging.error(f"Not found. {res.status_code=}, {res.reason=}, {url=}")
            return {}

        if res.status_code >= 400:
            logging.error(f"Failed GET. {res.status_code=}, {res.reason=}, {url=}. Will retry...")
            raise Exception

        return {}

    def get_season(self, region_id):
        """
        /sc2/ladder/season/:regionId
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower()) + f"/sc2/ladder/season/{region_id}"
        )

    def get_league(self, region_id, season_id, queue_id, team_type, league_id):
        """
        /data/sc2/league/{seasonId}/{queueId}/{teamType}/{leagueId}
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/data/sc2/league/{season_id}/{queue_id}/{team_type}/{league_id}"
        )

    def get_ladder(self, region_id, ladder_id):
        """
        /sc2/legacy/ladder/:regionId/:ladderId
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/legacy/ladder/{region_id}/{ladder_id}"
        )

    def get_match_history(self, region_id, realm_id, profile_id):
        """
        /sc2/legacy/profile/:regionId/:realmId/:profileId/matches
        """
        return self.get(
            url=BLIZZARD_API_BASE.format(region=RegionId(region_id).name.lower())
            + f"/sc2/legacy/profile/{region_id}/{realm_id}/{profile_id}/matches"
        )
