"""
ETL processes associated with SC2 ladder games
"""

from dataclasses import dataclass
from datetime import datetime

from backend.api.methods import SC2StatsAPI
from backend.blizzard.api import BlizzardApi
from backend.blizzard.models.legacy import LegacyMatchHistoryResponse
from backend.db.model import Match, Profile
from backend.enums import MatchType
from backend.etl.execution import conclude_etl_execution, initiate_etl_execution
from backend.etl.transform.match import reconcile_matches
from backend.static import MATCH_JOB_NAME
from backend.utils.concurrency import yield_futures
from backend.utils.datetime import datetime_to_epoch
from backend.utils.log import get_logger

# TODO refactor pairing logic to support game modes other than 1V1


logger = get_logger(__name__)


@dataclass
class ReconcileFuture:
    profile_id: int
    ladder_matches: list
    db_matches: list


def get_match_history_wrapper(profile):
    api = BlizzardApi()
    return LegacyMatchHistoryResponse.model_validate(
        api.get_legacy_match_history(
            region_id=profile.region_id,
            realm_id=profile.realm_id,
            profile_id=profile.profile_i,
        )
    )


def fetch_matches(region_id):
    bucketed_db_matches = {}
    bucketed_ladder_matches = {}

    logger.info(f"Fetching all unreconciled matches for {region_id=}")
    unreconciled_db_matches = [
        Match(**match) for match in SC2StatsAPI.get(endpoint=f"/match/unreconciled/{region_id}").get("results", [])
    ]
    logger.info(f"Found {len(unreconciled_db_matches)} unreconciled DB matches.")
    profile_ids = list({match.profile_id for match in unreconciled_db_matches})
    logger.info(f"Found {len(profile_ids)} profiles with unreconciled DB matches.")

    logger.info(f"Getting DB profiles for {region_id=}")
    profiles = [
        Profile(**profile)
        for profile in SC2StatsAPI.post(endpoint="/in/profile/id", data={"iterable": profile_ids}).get("results", [])
    ]
    if not profiles:
        logger.info(f"Did not find any profiles with unreconciled DB matches. {region_id=}")
    else:
        logger.info(f"Starting fetch of match history for {len(profiles)} profiles. {region_id=}")
        future_results = list(yield_futures(get_match_history_wrapper, profiles))
        for response, profile in future_results:
            logger.debug(f"Got {len(response.matches)} ladder matches for {profile.id} from Blizzard API.")
            ladder_matches = [match for match in response.matches if match.type == MatchType._1V1.value]
            bucketed_ladder_matches[profile.id] = ladder_matches

        logger.info(f"Starting fetch of DB matches for {len(profiles)} profiles. {region_id=}")
        for profile_id in profile_ids:
            db_matches = [
                Match(**match)
                for match in SC2StatsAPI.get(endpoint=f"/match/profile/{region_id}/{profile_id}").get("results", [])
            ]
            bucketed_db_matches[profile_id] = db_matches

    return bucketed_ladder_matches, bucketed_db_matches


def get_matches(**kwargs):
    logger.info("Starting fetch of recent matches.")
    start = datetime.now()

    region_id = kwargs.get("region_id")
    if not region_id:
        logger.warning("Missing required param region_id")
        return

    etl_execution = initiate_etl_execution(
        name=MATCH_JOB_NAME, region_id=region_id, start_timestamp=datetime_to_epoch(start)
    )

    bucketed_ladder_matches, bucketed_db_matches = fetch_matches(region_id)
    reconcile_futures = [
        ReconcileFuture(
            profile_id=profile_id,
            ladder_matches=bucketed_ladder_matches[profile_id],
            db_matches=list(bucketed_db_matches[profile_id]),
        )
        for profile_id in list(bucketed_db_matches)
    ]

    upsert = []
    delete = []
    for result, _ in yield_futures(reconcile_matches, reconcile_futures):
        upsert += result[0]
        delete += result[1]

    if delete:
        logger.info(f"Deleting {len(delete)} matches. {region_id=}")
        SC2StatsAPI.delete(endpoint="/in/match/id", data={"iterable": [match.id for match in delete]})

    if upsert:
        logger.info(f"Upserting {len(upsert)} matches. {region_id=}")
        # for u in upsert:
        #     logger.info(u)
        SC2StatsAPI.put(
            endpoint="/put/match",
            data={
                "rows": upsert,
                "set_": [
                    "map",
                    "type",
                    "decision",
                    "speed",
                    "start_timestamp",
                    "end_timestamp",
                    "duration",
                    "reconciled",
                ],
            },
        )

    end = datetime.now()
    conclude_etl_execution(etl_execution, end_timestamp=datetime_to_epoch(end))
    logger.info(f"Fetching recent matches took {round(end.timestamp() - start.timestamp())} seconds. {region_id=}")
    logger.info(f"Done with fetch of recent matches. {region_id=}")
