"""
Get league Ids for current season
"""

from more_itertools import one, only
from sqlalchemy import select
from backend.api.blizzard import BlizzardApi
from backend.db.db import Session, get_or_create
from backend.db.model import Ladder, League
from backend.enums import LeagueId, QueueId, RegionId, TeamType
from backend.api.models.league import LeagueResponse
from backend.api.models.season import SeasonResponse
import logging


def get_ladders():
    api = BlizzardApi()
    for region in RegionId:
        season = SeasonResponse.model_validate(api.get_season(region_id=region.value))
        for queue in QueueId:
            for team in TeamType:
                for league in LeagueId:
                    logging.info(
                        f"Processing {region.value=}, {season.season_id=}, {queue.value=}, {team.value=}, {league.value=}"
                    )
                    league_response = LeagueResponse.model_validate(
                        api.get_league(
                            region_id=region.value,
                            season_id=season.season_id,
                            queue_id=queue.value,
                            team_type=team.value,
                            league_id=league.value,
                        )
                    )

                    with Session() as session:
                        league = get_or_create(
                            session=session,
                            model=League,
                            constraint={
                                "league_id": league_response.key.league_id,
                                "season_id": league_response.key.season_id,
                                "queue_id": league_response.key.queue_id,
                                "team_type": league_response.key.team_type,
                            },
                            values={
                                "league_id": league_response.key.league_id,
                                "season_id": league_response.key.season_id,
                                "queue_id": league_response.key.queue_id,
                                "team_type": league_response.key.team_type,
                            },
                        )

                        for league_tier in league_response.tier:
                            for league_division in league_tier.division:
                                get_or_create(
                                    session=session,
                                    model=Ladder,
                                    constraint={
                                        "ladder_id": league_division.ladder_id,
                                        "league_id": league.id,
                                    },
                                    values={
                                        "ladder_id": league_division.ladder_id,
                                        "min_rating": league_tier.min_rating,
                                        "max_rating": league_tier.max_rating,
                                        "member_count": league_division.member_count,
                                        "league_id": league.id,
                                    },
                                )
