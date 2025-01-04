"""
ETL processes associated with SC2 match history
"""

import concurrent
import logging
import time
from datetime import datetime

from more_itertools import one

from backend.api.blizzard import BlizzardApi
from backend.api.models.match import MatchHistoryResponse
from backend.db.db import Session, query, upsert
from backend.db.model import Match, Profile
from backend.static import PROFILE_BATCH_SIZE
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

    profiles = query(params={Profile})
    logging.info(f"Will process match histories for {len(profiles)} profiles...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_match_history_wrapper, profile): profile for profile in profiles}
        for future in concurrent.futures.as_completed(futures):
            if processed != 0 and processed % PROFILE_BATCH_SIZE == 0:
                logging.info(
                    f"Processed {processed} profiles. " f"Last batch took {round(time.time() - batch_start)} seconds."
                )
                batch_start = time.time()

            match_history_response = future.result()
            match_history_response.profile = futures[future]
            yield match_history_response
            processed += 1


def get_matches():
    logging.info("Starting fetch of match histories...")
    start = datetime.now()
    profiles_processed = 0
    matches_processed = 0
    for match_history_response in process_match_histories():
        profiles_processed += 1
        with Session() as session:
            profile = one(query(params={Profile}, filters={"id": match_history_response.profile.id}))
            for match in match_history_response.matches:
                upsert(
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
                        "profile_id": profile.id,
                        "profile": profile,
                    },
                )
            matches_processed += 1

    end = datetime.now()
    logging.info(f"Processed {matches_processed} matches for {profiles_processed} characters.")
    logging.info(f"Processing match histories took {round(end.timestamp() - start.timestamp())} seconds.")
