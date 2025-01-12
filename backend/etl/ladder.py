"""
ETL processes associated with SC2 ladders
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.api.blizzard import BlizzardApi
from backend.api.models.game_data import LeagueResponse
from backend.api.models.ladder import SeasonResponse
from backend.db.db import (
    bulk_upsert,
    get_or_create,
    insert_stmt,
    orm_classes_as_dict,
    session_scope,
)
from backend.db.model import Ladder, League
from backend.enums import LeagueId, QueueId, TeamType
from backend.static import LADDER_UNIQUE_CONSTRAINT
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


def process_leagues(region_id):
    api = BlizzardApi()
    leagues = []

    season = SeasonResponse.model_validate(api.get_ladder_season(region_id=region_id))
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

                ladders = []
                for league_tier in league_response.tier:
                    for league_division in league_tier.division:
                        ladders.append(
                            Ladder(
                                **{
                                    "id": uuid.uuid4(),
                                    "ladder_id": league_division.ladder_id,
                                    "region_id": league_response.region_id,
                                    "min_rating": league_tier.min_rating,
                                    "max_rating": league_tier.max_rating,
                                    "member_count": league_division.member_count,
                                    "league_id": league.id,
                                }
                            ),
                        )
                if ladders:
                    stmt = insert_stmt(model=Ladder, values=orm_classes_as_dict(ladders))
                    bulk_upsert(
                        session,
                        stmt=stmt,
                        constraint=LADDER_UNIQUE_CONSTRAINT,
                        set_={
                            "min_rating": stmt.excluded.min_rating,
                            "max_rating": stmt.excluded.max_rating,
                            "member_count": stmt.excluded.member_count,
                        },
                    )

    end = datetime.now()
    logger.info(f"Updating leagues and ladders took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with fetch of current leagues and ladders.")
