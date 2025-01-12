"""
ETL processes associated with SC2 ladder members (Profile/Character)
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.api.blizzard import BlizzardApi
from backend.api.models.ladder import SeasonResponse
from backend.api.models.legacy import LegacyLadderResponse
from backend.db.db import (
    bulk_upsert,
    get_or_create,
    insert_stmt,
    orm_classes_as_dict,
    query,
    session_scope,
)
from backend.db.model import Character, Ladder, LadderMember, League, Profile
from backend.static import (
    CHARACTER_UNIQUE_CONSTRAINT,
    LADDER_BATCH_SIZE,
    LADDER_MEMBER_UNIQUE_CONSTRAINT,
)
from backend.utils.concurrency import yield_futures
from backend.utils.log import get_logger

logger = get_logger(__name__)


@dataclass
class LadderFuture:
    id: uuid.UUID
    region_id: int
    ladder_id: int


def get_legacy_ladder_wrapper(ladder_future):
    api = BlizzardApi()
    return LegacyLadderResponse.model_validate(
        api.get_legacy_ladder(region_id=ladder_future.region_id, ladder_id=ladder_future.ladder_id)
    )


def process_ladder(region_id):
    processed = 0
    batch_start = time.time()

    api = BlizzardApi()
    season = SeasonResponse.model_validate(api.get_ladder_season(region_id=region_id))
    with session_scope() as session:
        ladders = query(
            session,
            params={Ladder},
            joins=[(League, League.id == Ladder.league_id)],
            filters=[(Ladder.region_id == region_id), (League.season_id == season.season_id)],
        )
        ladder_futures = [
            LadderFuture(id=ladder.id, ladder_id=ladder.ladder_id, region_id=ladder.region_id) for ladder in ladders
        ]

    for result, ladder_future in yield_futures(func=get_legacy_ladder_wrapper, iterable=ladder_futures):
        if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
            logger.info(
                f"Have fetched {processed} ladders. " f"Last batch took {round(time.time() - batch_start)} seconds."
            )
            batch_start = time.time()

        if not ladder_future.id:
            print("HERE I AM")
            print(ladder_future)

        result.ladder_id = ladder_future.id
        yield result
        processed += 1
    logger.info(f"Done with fetch of ladders. Fetched {processed} total ladders.")


def get_ladder_members(**kwargs):
    logger.info("Starting fetch of ladder members (characters)...")
    start = datetime.now()
    processed_ladder_members = 0
    characters = []
    spent_characters = set()
    spent_ladder_members = set()
    ladder_members = []

    region_id = kwargs.get("region_id")
    if not region_id:
        logger.warning("Missing required param region_id")
        return

    for ladder_response in process_ladder(region_id=region_id):
        logger.info(f"Got response for ladder {ladder_response.ladder_id}...")
        for ladder_member in ladder_response.ladder_members:
            with session_scope() as session:
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
                character_lookup_key = f"{profile.id}_{ladder_member.character.display_name}"
                if character_lookup_key not in spent_characters:
                    character = Character(
                        **{
                            "id": uuid.uuid4(),
                            "display_name": ladder_member.character.display_name,
                            "clan_name": ladder_member.character.clan_name,
                            "clan_tag": ladder_member.character.clan_tag,
                            "profile_path": ladder_member.character.profile_path,
                            "profile_id": profile.id,
                        }
                    )
                    characters.append(character)
                    spent_characters.add(character_lookup_key)

                ladder_member_lookup_key = (
                    f"{ladder_member.character.profile_id}_{ladder_response.ladder_id}_{ladder_member.join_timestamp}"
                )
                if ladder_member_lookup_key not in spent_ladder_members:
                    ladder_member = LadderMember(
                        **{
                            "id": uuid.uuid4(),
                            "join_timestamp": ladder_member.join_timestamp,
                            "points": ladder_member.points,
                            "wins": ladder_member.wins,
                            "losses": ladder_member.losses,
                            "highest_rank": ladder_member.highest_rank,
                            "previous_rank": ladder_member.previous_rank,
                            "race": ladder_member.race,
                            "profile_id": profile.id,
                            "ladder_id": ladder_response.ladder_id,
                        }
                    )
                    ladder_members.append(ladder_member)
                    spent_ladder_members.add(ladder_member_lookup_key)

                processed_ladder_members += 1

    with session_scope() as session:
        if characters:
            logger.info(f"Upserting {len(characters)} characters...")
            stmt = insert_stmt(model=Character, values=orm_classes_as_dict(characters))
            bulk_upsert(
                session,
                stmt=stmt,
                constraint=CHARACTER_UNIQUE_CONSTRAINT,
                set_={
                    "clan_name": stmt.excluded.clan_name,
                    "clan_tag": stmt.excluded.clan_tag,
                },
            )

        if ladder_members:
            logger.info(f"Upserting {len(ladder_members)} ladder members...")
            stmt = insert_stmt(model=LadderMember, values=orm_classes_as_dict(ladder_members))
            bulk_upsert(
                session,
                stmt=stmt,
                constraint=LADDER_MEMBER_UNIQUE_CONSTRAINT,
                set_={
                    "points": stmt.excluded.points,
                    "wins": stmt.excluded.wins,
                    "losses": stmt.excluded.losses,
                    "highest_rank": stmt.excluded.highest_rank,
                    "previous_rank": stmt.excluded.previous_rank,
                },
            )

    end = datetime.now()
    logger.info(f"Processed {processed_ladder_members} ladder members.")
    logger.info(f"Processing characters took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with fetch of ladder members.")
