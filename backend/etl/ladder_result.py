"""
ETL processes associated with SC2 ladder results (MMR, Game duration, Etc.)
"""

import time
import uuid
from datetime import datetime

from more_itertools import first, only

from backend.api.blizzard import BlizzardApi
from backend.api.models.legacy import LegacyMatchHistoryResponse
from backend.api.models.profile import ProfileLadderResponse
from backend.db.db import (
    bulk_insert,
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
from backend.static import LADDER_BATCH_SIZE
from backend.utils.concurrency_utils import get_task_manager
from backend.utils.datetime_utils import current_epoch_time
from backend.utils.logging_utils import get_logger

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


def get_match_history_wrapper(profile):
    api = BlizzardApi()
    return LegacyMatchHistoryResponse.model_validate(
        api.get_legacy_match_history(
            region_id=profile.region_id,
            realm_id=profile.realm_id,
            profile_id=profile.profile_id,
        )
    )


def query_character(session, team_member):
    try:
        return only(
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
    except ValueError:
        logger.error(f"Found multiple character entries for {team_member=}")

    return None


def query_character_mmr(session, character, team_member):
    try:
        return query(
            session,
            params={CharacterMMR},
            filters=[(CharacterMMR.character == character), (CharacterMMR.race == team_member.race)],
            order_by=CharacterMMR.date.desc(),
        )
    except Exception:
        logger.exception(f"Exception thrown querying for character MMR. {character=} {team_member=}")

    return None


def process_profile_ladder_response(profile_ladder_response):
    with session_scope() as session:
        character_mmrs = []
        matches = []
        for ladder_team in profile_ladder_response.ladder_teams:
            if not ladder_team.mmr:
                continue

            for team_member in ladder_team.team_members:
                if not team_member.race:
                    continue

                character = query_character(session, team_member)
                if not character:
                    logger.warning(f"Unable to find character for {team_member=}")
                    continue

                character_mmr = query_character_mmr(session, character, team_member)
                db_mmr = first(character_mmr).mmr if len(character_mmr) > 0 else None
                ladder_mmr = ladder_team.mmr
                if not character_mmr or db_mmr != ladder_mmr:
                    logger.info(
                        f"New MMR result for {character.display_name}:{character.profile_path}. "
                        + f"{db_mmr} --> {ladder_mmr}"
                    )
                    character_mmrs.append(
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
                        profile = character.profile
                        match_history_response = get_match_history_wrapper(profile)
                        if match_history_response.matches:
                            match = first(
                                sorted(match_history_response.matches, key=lambda match: match.date, reverse=True)
                            )
                            matches.append(
                                Match(
                                    **{
                                        "id": uuid.uuid4(),
                                        "date": match.date,
                                        "map": match.map,
                                        "type": match.type,
                                        "decision": match.decision,
                                        "speed": match.speed,
                                        "duration": current_epoch_time() - match.date,
                                        "profile_id": profile.id,
                                    }
                                )
                            )

        return (matches, character_mmrs)


def process_profile_ladder():
    processed = 0
    batch_start = time.time()
    with session_scope() as session:
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
            distinct={LadderMember.ladder_id},
        )

        for result, ladder_member in get_task_manager().yield_futures(get_profile_ladder_wrapper, ladder_members):
            if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
                logger.info(
                    f"Processed {processed} ladders. " f"Last batch took {round(time.time() - batch_start)} seconds."
                )
                batch_start = time.time()

            result.ladder_member = ladder_member
            yield result
            processed += 1


def get_ladder_results():
    logger.info("Starting fetch of ladder results...")
    ladders_processed = 0
    start = datetime.now()

    matches = []
    character_mmrs = []
    for res, _ in get_task_manager().yield_futures(process_profile_ladder_response, process_profile_ladder()):
        ladders_processed += 1
        ladder_matches, ladder_character_mmrs = res
        matches = matches + ladder_matches
        character_mmrs = character_mmrs + ladder_character_mmrs

    with session_scope() as session:
        if character_mmrs:
            stmt = insert_stmt(model=CharacterMMR, values=orm_classes_as_dict(character_mmrs))
            bulk_insert(
                session,
                stmt=stmt,
                constraint="character_mmr_unique_constraint",
            )

        if matches:
            stmt = insert_stmt(model=Match, values=orm_classes_as_dict(matches))
            bulk_insert(
                session,
                stmt=stmt,
                constraint="match_unique_constraint",
            )

    end = datetime.now()
    logger.info(f"Processed a total of {ladders_processed} ladders.")
    logger.info(f"Processing ladder results took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with fetch of ladder results.")
