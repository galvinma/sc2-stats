"""
ETL processes associated with SC2 ladder results (MMR, Game duration, Etc.)
"""

import concurrent
import logging
import time
from datetime import datetime
from multiprocessing.pool import ThreadPool

from more_itertools import first, only

from backend.api.blizzard import BlizzardApi
from backend.api.models.legacy import LegacyMatchHistoryResponse
from backend.api.models.profile import ProfileLadderResponse
from backend.db.db import Session, get_or_create, insert, query
from backend.db.model import (
    Character,
    CharacterMMR,
    Ladder,
    LadderMember,
    Match,
    Profile,
)
from backend.static import LADDER_BATCH_SIZE
from backend.utils.concurrency_utils import thread_pool_max_workers
from backend.utils.datetime_utils import current_epoch_time

# TODO refactor this ETL for team types beyond 1v1


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
        logging.error(f"Found multiple character entries for {team_member=}")

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
        logging.exception(f"Exception thrown querying for character MMR. {character=} {team_member=}")

    return None


def insert_character_mmr(session, character, ladder_team, team_member):
    insert(
        session,
        model=CharacterMMR,
        values={
            "race": team_member.race,
            "mmr": ladder_team.mmr,
            "date": current_epoch_time(),
            "character_id": character.id,
            "character": character,
        },
    )


def insert_match(session, profile, match):
    return get_or_create(
        session=session,
        model=Match,
        filter={
            "profile_id": profile.id,
            "date": match.date,
        },
        values={
            "date": match.date,
            "map": match.map,
            "type": match.type,
            "decision": match.decision,
            "speed": match.speed,
            "duration": current_epoch_time() - match.date,
            "profile_id": profile.id,
            "profile": profile,
        },
    )


def process_ladder_team_member(session, ladder_team, team_member):
    character = query_character(session, team_member)
    if not character:
        logging.warning(f"Unable to find character for {team_member=}")
        return None

    character_mmr = query_character_mmr(session, character, team_member)
    db_mmr = first(character_mmr).mmr if len(character_mmr) > 0 else None
    ladder_mmr = ladder_team.mmr
    if not character_mmr or db_mmr != ladder_mmr:
        logging.info(f"New MMR result for {character.display_name}:{character.profile_path}. {db_mmr} --> {ladder_mmr}")
        insert_character_mmr(session, character, ladder_team, team_member)

        # Fetch match history and calculate game duration if we have a baseline MMR
        if db_mmr is not None:
            profile = character.profile
            match_history_response = get_match_history_wrapper(profile)
            if match_history_response.matches:
                matches = sorted(match_history_response.matches, key=lambda match: match.date, reverse=True)
                match = first(matches)
                insert_match(session, profile, match)


def process_profile_ladder_response(profile_ladder_response):
    for ladder_team in profile_ladder_response.ladder_teams:
        if not ladder_team.mmr:
            continue

        for team_member in ladder_team.team_members:
            if not team_member.race:
                continue

            with Session() as session:
                process_ladder_team_member(session, ladder_team, team_member)


def process_profile_ladder():
    processed = 0
    batch_start = time.time()
    with Session() as session:
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_pool_max_workers()) as executor:
            futures = {
                executor.submit(get_profile_ladder_wrapper, ladder_member): ladder_member
                for ladder_member in ladder_members
            }

            for future in concurrent.futures.as_completed(futures):
                if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
                    logging.info(
                        f"Processed {processed} ladders. "
                        f"Last batch took {round(time.time() - batch_start)} seconds."
                    )
                    batch_start = time.time()

                profile_ladder_response = future.result()
                profile_ladder_response.ladder_member = futures[future]
                yield profile_ladder_response
                processed += 1


def get_ladder_results():
    logging.info("Starting fetch of ladder results...")
    ladders_processed = 0
    start = datetime.now()

    with ThreadPool(processes=thread_pool_max_workers()) as pool:
        for _ in pool.imap(process_profile_ladder_response, process_profile_ladder()):
            ladders_processed += 1

    end = datetime.now()
    logging.info(f"Processed a total of {ladders_processed} ladders.")
    logging.info(f"Processing ladder results took {round(end.timestamp() - start.timestamp())} seconds.")
