"""
ETL processes associated with SC2 ladders
"""

from dataclasses import dataclass
from datetime import datetime

from more_itertools import one

from backend.api.methods import SC2StatsAPI
from backend.blizzard.api import BlizzardApi
from backend.blizzard.models.game_data import LeagueResponse
from backend.blizzard.models.ladder import SeasonResponse
from backend.db.model import League
from backend.enums import LeagueId, QueueId, TeamType
from backend.utils.concurrency import yield_futures
from backend.utils.log import get_logger

logger = get_logger(__name__)


@dataclass
class LeagueFuture:
    region_id: int
    season_id: int
    queue_id: int
    team_type: int
    league_id: int


def get_league_wrapper(league_future):
    blizzard_api = BlizzardApi()
    return LeagueResponse.model_validate(
        blizzard_api.get_league(
            region_id=league_future.region_id,
            season_id=league_future.season_id,
            queue_id=league_future.queue_id,
            team_type=league_future.team_type,
            league_id=league_future.league_id,
        )
    )


def process_leagues(region_id):
    blizzard_api = BlizzardApi()
    leagues = []

    season = SeasonResponse.model_validate(blizzard_api.get_ladder_season(region_id=region_id))
    for queue in QueueId:
        for team in TeamType:
            for league in LeagueId:
                leagues.append(
                    LeagueFuture(
                        region_id=region_id,
                        season_id=season.season_id,
                        queue_id=queue.value,
                        team_type=team.value,
                        league_id=league.value,
                    )
                )

    for result, league in yield_futures(get_league_wrapper, leagues):
        result.region_id = league.region_id
        yield result


def get_ladders(**kwargs):
    logger.info("Starting fetch of current leagues and ladders...")
    start = datetime.now()

    region_id = kwargs.get("region_id")
    if not region_id:
        logger.warning("Missing required param region_id")
        return

    for league_response in process_leagues(region_id=region_id):
        if league_response and league_response.key:
            values = {
                "region_id": league_response.region_id,
                "league_id": league_response.key.league_id,
                "season_id": league_response.key.season_id,
                "queue_id": league_response.key.queue_id,
                "team_type": league_response.key.team_type,
            }
            SC2StatsAPI.put(
                endpoint="/put/league",
                data={
                    "rows": [values],
                },
            )
            league = League(
                **one(
                    SC2StatsAPI.get(
                        endpoint="/get/league",
                        params=values,
                    ).get("results")
                )
            )

            ladders = []
            for league_tier in league_response.tier:
                for league_division in league_tier.division:
                    ladders.append(
                        {
                            "ladder_id": league_division.ladder_id,
                            "region_id": league_response.region_id,
                            "min_rating": league_tier.min_rating,
                            "max_rating": league_tier.max_rating,
                            "member_count": league_division.member_count,
                            "league_id": league.id,
                        }
                    )
            if ladders:
                SC2StatsAPI.put(
                    endpoint="/put/ladder",
                    data={"rows": ladders, "set_": ["min_rating", "max_rating", "member_count"]},
                )

    end = datetime.now()
    logger.info(f"Updating leagues and ladders took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with fetch of current leagues and ladders.")
