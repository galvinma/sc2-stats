"""
ETL processes associated with SC2 characters
"""

import concurrent
import logging
import time
from datetime import datetime

from more_itertools import one

from backend.api.blizzard import BlizzardApi
from backend.api.models.ladder import LadderResponse
from backend.db.db import Session, get_or_create, query, upsert
from backend.db.model import Character, Ladder, LadderMember, Profile
from backend.static import LADDER_BATCH_SIZE
from backend.utils import thread_pool_max_workers


def get_ladder_wrapper(ladder):
    api = BlizzardApi()
    return LadderResponse.model_validate(api.get_ladder(region_id=ladder.region_id, ladder_id=ladder.ladder_id))


def process_ladder():
    max_workers = thread_pool_max_workers()
    logging.info(f"Will process ladders with {max_workers=}")

    processed = 0
    batch_start = time.time()

    ladders = query(params={Ladder})
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_ladder_wrapper, ladder): ladder for ladder in ladders}

        for future in concurrent.futures.as_completed(futures):
            if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
                logging.info(
                    f"Processed {processed} ladders. " f"Last batch took {round(time.time() - batch_start)} seconds."
                )
                batch_start = time.time()

            ladder_response = future.result()
            ladder_response.ladder = futures[future]
            yield ladder_response
            processed += 1


def get_characters():
    logging.info("Starting fetch of ladder members (characters)...")
    start = datetime.now()
    processed_ladder_members = 0
    for ladder_response in process_ladder():
        for ladder_member in ladder_response.ladder_members:
            with Session() as session:
                ladder = one(query(params={Ladder}, filters={"id": ladder_response.ladder.id}))
                profile = get_or_create(
                    session=session,
                    model=Profile,
                    filter={
                        "profile_id": ladder_member.character.profile_id,
                        "realm_id": ladder_member.character.realm_id,
                        "region_id": ladder_member.character.region_id,
                    },
                    values={
                        "profile_id": ladder_member.character.profile_id,
                        "realm_id": ladder_member.character.realm_id,
                        "region_id": ladder_member.character.region_id,
                    },
                )
                upsert(
                    session=session,
                    model=Character,
                    filter={
                        "profile_id": profile.id,
                        "display_name": ladder_member.character.display_name,
                    },
                    values={
                        "display_name": ladder_member.character.display_name,
                        "clan_name": ladder_member.character.clan_name,
                        "clan_tag": ladder_member.character.clan_tag,
                        "profile_path": ladder_member.character.profile_path,
                        "profile_id": profile.id,
                        "profile": profile,
                    },
                )
                upsert(
                    session=session,
                    model=LadderMember,
                    filter={
                        "profile_id": profile.id,
                        "ladder_id": ladder.id,
                        "join_timestamp": ladder_member.join_timestamp,
                    },
                    values={
                        "join_timestamp": ladder_member.join_timestamp,
                        "points": ladder_member.points,
                        "wins": ladder_member.wins,
                        "losses": ladder_member.losses,
                        "highest_rank": ladder_member.highest_rank,
                        "previous_rank": ladder_member.previous_rank,
                        "favorite_race_p1": ladder_member.favorite_race_p1,
                        "profile_id": profile.id,
                        "profile": profile,
                        "ladder_id": ladder.id,
                        "ladder": ladder,
                    },
                )

            processed_ladder_members += 1

    end = datetime.now()
    logging.info(f"Processed {processed_ladder_members} ladder members.")
    logging.info(f"Processing characters took {round(end.timestamp() - start.timestamp())} seconds.")
