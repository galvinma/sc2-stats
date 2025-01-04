"""
ETL processes associated with SC2 match history
"""

import concurrent
import logging
import time
from datetime import datetime

from backend.api.blizzard import BlizzardApi
from backend.api.models.match import MatchHistoryResponse
from backend.db.db import Session, query, upsert
from backend.db.model import Character, Match
from backend.static import CHARACTER_BATCH_SIZE
from backend.utils import thread_pool_max_workers


def get_match_history_wrapper(character):
    api = BlizzardApi()
    return MatchHistoryResponse.model_validate(
        api.get_match_history(
            region_id=character.region_id,
            realm_id=character.realm_id,
            profile_id=character.profile_id,
        )
    )


def process_match_histories():
    max_workers = thread_pool_max_workers()
    logging.info(f"Will process match histories with {max_workers=}")

    processed = 0
    batch_start = time.time()

    characters = query(params={Character.id, Character.profile_id, Character.region_id, Character.realm_id})
    logging.info(f"Will process match histories for {len(characters)} characters...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_match_history_wrapper, character): character for character in characters}

        for future in concurrent.futures.as_completed(futures):
            if processed != 0 and processed % CHARACTER_BATCH_SIZE == 0:
                logging.info(
                    f"Processed {processed} characters. " f"Last batch took {round(time.time() - batch_start)} seconds."
                )
                batch_start = time.time()

            character = futures[future]
            match_history_response = future.result()
            match_history_response.character_id = character.id
            match_history_response.profile_id = character.profile_id
            match_history_response.region_id = character.region_id
            match_history_response.realm_id = character.realm_id
            yield match_history_response
            processed += 1


def get_matches():
    logging.info("Starting fetch of match histories...")
    start = datetime.now()
    characters_processed = 0
    matches_processed = 0
    for match_history_response in process_match_histories():
        characters_processed += 1
        for match in match_history_response.matches:
            with Session() as session:
                upsert(
                    session=session,
                    model=Match,
                    filter={
                        "character_id": match_history_response.character_id,
                        "profile_id": match_history_response.profile_id,
                        "region_id": match_history_response.region_id,
                        "realm_id": match_history_response.realm_id,
                        "date": match.date,
                    },
                    values={
                        "character_id": match_history_response.character_id,
                        "profile_id": match_history_response.profile_id,
                        "region_id": match_history_response.region_id,
                        "realm_id": match_history_response.realm_id,
                        "date": match.date,
                        "map": match.map,
                        "type": match.type,
                        "decision": match.decision,
                        "speed": match.speed,
                    },
                )
            matches_processed += 1

    end = datetime.now()
    logging.info(f"Processed {matches_processed} matches for {characters_processed} characters.")
    logging.info(f"Processing match histories took {round(end.timestamp() - start.timestamp())} seconds.")
