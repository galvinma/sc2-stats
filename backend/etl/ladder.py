"""
ETL processes associated with SC2 ladders
"""

from dataclasses import dataclass
from datetime import datetime

from backend.api.blizzard import BlizzardApi
from backend.api.models.game_data import LeagueResponse
from backend.api.models.ladder import SeasonResponse
from backend.db.db import get_or_create, session_scope, upsert
from backend.db.model import Ladder, League
from backend.enums import LeagueId, QueueId, RegionId, TeamType
from backend.utils.concurrency_utils import get_task_manager
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class LeagueFuture:
    region_id: int
    season_id: int
    queue_id: int
    team_type: int
    league_id: int


def get_league_wrapper(league_future):
    api = BlizzardApi()
    return LeagueResponse.model_validate(
        api.get_league(
            region_id=league_future.region_id,
            season_id=league_future.season_id,
            queue_id=league_future.queue_id,
            team_type=league_future.team_type,
            league_id=league_future.league_id,
        )
    )


def process_leagues():
    api = BlizzardApi()
    leagues = []
    for region in RegionId:
        season = SeasonResponse.model_validate(api.get_ladder_season(region_id=region.value))
        for queue in QueueId:
            for team in TeamType:
                for league in LeagueId:
                    leagues.append(
                        LeagueFuture(
                            region_id=region.value,
                            season_id=season.season_id,
                            queue_id=queue.value,
                            team_type=team.value,
                            league_id=league.value,
                        )
                    )

    for result, league in get_task_manager().yield_futures(get_league_wrapper, leagues):
        result.region_id = league.region_id
        yield result


def get_ladders():
    logger.info("Starting fetch of current leagues and ladders...")
    start = datetime.now()
    for league_response in process_leagues():
        with session_scope() as session:
            league = get_or_create(
                session,
                model=League,
                filter={
                    "region_id": league_response.region_id,
                    "league_id": league_response.key.league_id,
                    "season_id": league_response.key.season_id,
                    "queue_id": league_response.key.queue_id,
                    "team_type": league_response.key.team_type,
                },
                values={
                    "region_id": league_response.region_id,
                    "league_id": league_response.key.league_id,
                    "season_id": league_response.key.season_id,
                    "queue_id": league_response.key.queue_id,
                    "team_type": league_response.key.team_type,
                },
            )

            for league_tier in league_response.tier:
                for league_division in league_tier.division:
                    upsert(
                        session,
                        model=Ladder,
                        filter={
                            "region_id": league_response.region_id,
                            "ladder_id": league_division.ladder_id,
                            "league_id": league.id,
                        },
                        values={
                            "ladder_id": league_division.ladder_id,
                            "region_id": league_response.region_id,
                            "min_rating": league_tier.min_rating,
                            "max_rating": league_tier.max_rating,
                            "member_count": league_division.member_count,
                            "league_id": league.id,
                        },
                    )

    end = datetime.now()
    logger.info(f"Updating leagues and ladders took {round(end.timestamp() - start.timestamp())} seconds.")
