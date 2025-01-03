"""
ETL processes associated with SC2 ladders
"""

import concurrent
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime

from backend.api.blizzard import BlizzardApi
from backend.api.models.ladder import LadderResponse
from backend.api.models.league import LeagueResponse
from backend.api.models.season import SeasonResponse
from backend.db.db import Session, get_or_create, query, upsert
from backend.db.model import Character, Ladder, League
from backend.enums import LeagueId, QueueId, RegionId, TeamType
from backend.static import BATCH_SIZE, MAX_WORKERS


def get_ladders():
    api = BlizzardApi()
    start = datetime.now()
    for region in RegionId:
        season = SeasonResponse.model_validate(api.get_season(region_id=region.value))
        for queue in QueueId:
            for team in TeamType:
                for league in LeagueId:
                    logging.info(
                        f"Processing {region.value=}, {season.season_id=}, "
                        + f"{queue.value=}, {team.value=}, {league.value=}"
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
                            filter={
                                "region_id": region.value,
                                "league_id": league_response.key.league_id,
                                "season_id": league_response.key.season_id,
                                "queue_id": league_response.key.queue_id,
                                "team_type": league_response.key.team_type,
                            },
                            values={
                                "region_id": region.value,
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
                                        "region_id": region.value,
                                        "ladder_id": league_division.ladder_id,
                                        "league_id": league.id,
                                    },
                                    values={
                                        "ladder_id": league_division.ladder_id,
                                        "region_id": region.value,
                                        "min_rating": league_tier.min_rating,
                                        "max_rating": league_tier.max_rating,
                                        "member_count": league_division.member_count,
                                        "league_id": league.id,
                                    },
                                )
    end = datetime.now()
    logging.info(f"Updating leagues and ladders took {round(end.timestamp() - start.timestamp())} seconds.")


def process_ladder(ladder_future):
    api = BlizzardApi()
    return LadderResponse.model_validate(
        api.get_ladder(region_id=ladder_future.region_id, ladder_id=ladder_future.ladder_id)
    )


@dataclass
class LadderFuture:
    region_id: int
    ladder_id: int


def get_ladder_members():
    max_workers = os.cpu_count() if os.cpu_count() <= MAX_WORKERS else MAX_WORKERS
    logging.info(f"Will process ladders with {max_workers=}")

    processed = 0
    start = datetime.now()
    batch_start = time.time()
    ladder_responses = []
    for region in RegionId:
        ladders = query(Ladder, {"region_id": region.value})
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_ladder, LadderFuture(region_id=region.value, ladder_id=ladder.ladder_id))
                for ladder in ladders
            }
            for future in concurrent.futures.as_completed(futures):
                if processed != 0 and processed % BATCH_SIZE == 0:
                    logging.info(
                        f"Processed {processed} ladders. "
                        f"Last batch took {round(time.time() - batch_start)} seconds."
                    )
                    batch_start = time.time()

                ladder_responses.append(future.result())
                processed += 1

    logging.info(f"Done with fetch. Will process characters from {len(ladder_responses)} ladders...")
    int(len(ladder_responses) / 100)
    processed = 0
    batch_start = time.time()
    for ladder_response in ladder_responses:
        for ladder_member in ladder_response.ladder_members:
            with Session() as session:
                upsert(
                    session=session,
                    model=Character,
                    filter={
                        "character_id": ladder_member.character.id,
                        "realm": ladder_member.character.realm,
                        "region": ladder_member.character.region,
                    },
                    values={
                        "character_id": ladder_member.character.id,
                        "realm": ladder_member.character.realm,
                        "region": ladder_member.character.region,
                        "display_name": ladder_member.character.display_name,
                        "clan_name": ladder_member.character.clan_name,
                        "clan_tag": ladder_member.character.clan_tag,
                        "profile_path": ladder_member.character.profile_path,
                        "join_timestamp": ladder_member.join_timestamp,
                        "points": ladder_member.points,
                        "wins": ladder_member.wins,
                        "losses": ladder_member.losses,
                        "highest_rank": ladder_member.highest_rank,
                        "previous_rank": ladder_member.previous_rank,
                        "favorite_race_p1": ladder_member.favorite_race_p1,
                    },
                )

            if processed != 0 and processed % (BATCH_SIZE * 100) == 0:
                logging.info(
                    f"Processed {processed} characters. " f"Last batch took {round(time.time() - batch_start)} seconds."
                )
                batch_start = time.time()
            processed += 1

    end = datetime.now()
    logging.info(f"Updating ladder members took {round(end.timestamp() - start.timestamp())} seconds.")
