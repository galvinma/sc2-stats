"""
ETL processes associated with SC2 ladder members (Profile/Character)
"""

import time
from datetime import datetime

from more_itertools import one

from backend.api.blizzard import BlizzardApi
from backend.api.models.legacy import LegacyLadderResponse
from backend.db.db import get_or_create, query, session_scope, upsert
from backend.db.model import Character, Ladder, LadderMember, Profile
from backend.static import LADDER_BATCH_SIZE
from backend.utils.concurrency_utils import get_task_manager
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_legacy_ladder_wrapper(ladder):
    api = BlizzardApi()
    return LegacyLadderResponse.model_validate(
        api.get_legacy_ladder(region_id=ladder.region_id, ladder_id=ladder.ladder_id)
    )


def process_ladder():
    processed = 0
    batch_start = time.time()

    with session_scope() as session:
        ladders = query(session, params={Ladder})
        for result, ladder in get_task_manager().yield_futures(get_legacy_ladder_wrapper, ladders):
            if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
                logger.info(
                    f"Processed {processed} ladders. " f"Last batch took {round(time.time() - batch_start)} seconds."
                )
                batch_start = time.time()

            result.ladder = ladder
            yield result
            processed += 1


def get_ladder_members():
    logger.info("Starting fetch of ladder members (characters)...")
    start = datetime.now()
    processed_ladder_members = 0
    for ladder_response in process_ladder():
        for ladder_member in ladder_response.ladder_members:
            with session_scope() as session:
                ladder = one(query(session, params={Ladder}, filters=[(Ladder.id == ladder_response.ladder.id)]))
                profile = get_or_create(
                    session,
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
                    session,
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
                    session,
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
                        "race": ladder_member.race,
                        "profile_id": profile.id,
                        "profile": profile,
                        "ladder_id": ladder.id,
                        "ladder": ladder,
                    },
                )

            processed_ladder_members += 1

    end = datetime.now()
    logger.info(f"Processed {processed_ladder_members} ladder members.")
    logger.info(f"Processing characters took {round(end.timestamp() - start.timestamp())} seconds.")
