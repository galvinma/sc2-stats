"""
ETL processes associated with SC2 ladder results (MMR, Game duration, Etc.)
"""

import time
import uuid
from datetime import datetime

from more_itertools import only

from backend.api.blizzard import BlizzardApi
from backend.api.models.profile import ProfileLadderResponse
from backend.db.db import (
    bulk_insert,
    get_engine,
    insert_stmt,
    orm_classes_as_dict,
    query,
    session_scope,
)
from backend.db.model import (
    Character,
    CharacterMMR,
    Ladder,
    LadderMember,
    Match,
    Profile,
)
from backend.static import CHARACTER_MMR_UNIQUE_CONSTRAINT, LADDER_BATCH_SIZE
from backend.utils.concurrency import yield_futures
from backend.utils.datetime import current_epoch_time
from backend.utils.log import get_logger

# TODO refactor this ETL for team types beyond 1v1

logger = get_logger(__name__)


def get_profile_ladder_wrapper(ladder_member):
    api = BlizzardApi()
    return ProfileLadderResponse.model_validate(
        api.get_profile_ladder(
            region_id=ladder_member.region_id,
            realm_id=ladder_member.realm_id,
            profile_id=ladder_member.profile_id,
            ladder_id=ladder_member.ladder_id,
        )
    )


def process_profile_ladder(engine, region_id):
    processed = 0
    batch_start = time.time()
    with session_scope(engine=engine) as session:
        ladder_members = query(
            session,
            params={
                LadderMember.id,
                Ladder.ladder_id,
                Profile.id,
                Profile.region_id,
                Profile.realm_id,
                Profile.profile_id,
            },
            joins=[(Profile, Profile.id == LadderMember.profile_id), (Ladder, Ladder.id == LadderMember.ladder_id)],
            filters=[(Ladder.region_id == region_id)],
            distinct={LadderMember.ladder_id},
        )

    for profile_ladder_response, ladder_member in yield_futures(get_profile_ladder_wrapper, ladder_members):
        if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
            logger.info(
                f"Have fetched {processed} ladders. " f"Last batch took {round(time.time() - batch_start)} seconds."
            )
            batch_start = time.time()

        profile_ladder_response.ladder_member = ladder_member
        yield profile_ladder_response
        processed += 1

    logger.info(f"Done with fetch of ladders. Fetched {processed} total ladders.")


def get_ladder_results(**kwargs):
    logger.info("Starting fetch of ladder results...")
    ladders_processed = 0
    start = datetime.now()
    engine = get_engine()

    region_id = kwargs.get("region_id")
    if not region_id:
        logger.warning("Missing required param region_id")
        return

    responses = []
    for profile_ladder_response in process_profile_ladder(engine=engine, region_id=region_id):
        ladders_processed += 1
        responses.append(profile_ladder_response)

    process_profile_ladder_responses(engine, responses)

    end = datetime.now()
    logger.info(f"Processed a total of {ladders_processed} ladders.")
    logger.info(f"Processing ladder results took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with fetch of ladder results.")


def process_profile_ladder_response(response):
    engine = get_engine()
    mmrs = []
    matches = []
    for ladder_team in response.ladder_teams:
        if not ladder_team.mmr:
            continue

        for team_member in ladder_team.team_members:
            if not team_member.race:
                continue

        with session_scope(engine=engine) as session:
            db_character_mmr = only(
                query(
                    session,
                    params={CharacterMMR},
                    joins=[
                        (Character, Character.id == CharacterMMR.character_id),
                        (Profile, Profile.id == Character.profile_id),
                    ],
                    filters=[
                        (Profile.profile_id == team_member.profile_id),
                        (Profile.realm_id == team_member.realm_id),
                        (Profile.region_id == team_member.region_id),
                        (Character.display_name == team_member.display_name),
                        (CharacterMMR.race == team_member.race),
                    ],
                    order_by=CharacterMMR.date.desc(),
                    limit=1,
                )
            )
            db_mmr = db_character_mmr.mmr if db_character_mmr else None
            if db_mmr != ladder_team.mmr:
                if not db_character_mmr:
                    character = only(
                        query(
                            session,
                            params={Character},
                            joins=[(Profile, Profile.id == Character.profile_id)],
                            filters=[
                                (Profile.profile_id == team_member.profile_id),
                                (Profile.realm_id == team_member.realm_id),
                                (Profile.region_id == team_member.region_id),
                                (Character.display_name == team_member.display_name),
                            ],
                        )
                    )
                else:
                    character = db_character_mmr.character

                if not character:
                    continue

                logger.info(
                    f"New MMR result for {character.id}:{team_member.display_name}:{team_member.race.value} "
                    + f"{db_mmr} --> {ladder_team.mmr}"
                )
                mmrs.append(
                    CharacterMMR(
                        **{
                            "id": uuid.uuid4(),
                            "race": team_member.race,
                            "mmr": ladder_team.mmr,
                            "date": current_epoch_time(),
                            "character_id": character.id,
                        }
                    )
                )

                if db_mmr is not None:
                    # TODO determine decision options here
                    # decision = "Loss" if db_mmr > ladder_team.mmr else "Win"
                    matches.append(
                        Match(
                            **{
                                "id": uuid.uuid4(),
                                "end_date": current_epoch_time(),
                                # "decision": decision,
                                "profile_id": character.profile_id,
                            }
                        )
                    )

    return (mmrs, matches)


def process_profile_ladder_responses(engine, responses):
    character_mmrs = []
    matches = []

    for res, _ in yield_futures(process_profile_ladder_response, responses):
        ladder_mmrs, ladder_matches = res
        character_mmrs = character_mmrs + ladder_mmrs
        matches = matches + ladder_matches

    with session_scope(engine=engine) as session:
        if character_mmrs:
            stmt = insert_stmt(model=CharacterMMR, values=orm_classes_as_dict(character_mmrs))
            bulk_insert(
                session,
                stmt=stmt,
                constraint=CHARACTER_MMR_UNIQUE_CONSTRAINT,
            )

        if matches:
            stmt = insert_stmt(model=Match, values=orm_classes_as_dict(matches))
            bulk_insert(session, stmt=stmt, constraint=None)
