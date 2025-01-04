"""
ETL processes associated with SC2 ladders
"""

import concurrent
import logging
from dataclasses import dataclass
from datetime import datetime

from backend.api.blizzard import BlizzardApi
from backend.api.models.league import LeagueResponse
from backend.api.models.season import SeasonResponse
from backend.db.db import Session, get_or_create, upsert
from backend.db.model import Ladder, League
from backend.enums import LeagueId, QueueId, RegionId, TeamType
from backend.utils import thread_pool_max_workers


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
    max_workers = thread_pool_max_workers()
    logging.info(f"Will process leagues with {max_workers=}")

    api = BlizzardApi()
    leagues = []
    for region in RegionId:
        season = SeasonResponse.model_validate(api.get_season(region_id=region.value))
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_league_wrapper, league): league for league in leagues}
        for future in concurrent.futures.as_completed(futures):

            league_future = futures[future]
            league_response = future.result()
            league_response.region_id = league_future.region_id
            yield future.result()


def get_ladders():
    logging.info("Starting fetch of current leagues and ladders...")
    start = datetime.now()
    for league_response in process_leagues():

        with Session() as session:
            league = get_or_create(
                session=session,
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
                        session=session,
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
    logging.info(f"Updating leagues and ladders took {round(end.timestamp() - start.timestamp())} seconds.")