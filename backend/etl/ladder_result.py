"""
ETL processes associated with SC2 ladder results (MMR, Game duration, Etc.)
"""

from collections import defaultdict
from datetime import datetime

from more_itertools import one

from backend.api.methods import SC2StatsAPI
from backend.blizzard.api import BlizzardApi
from backend.blizzard.models.ladder import SeasonResponse
from backend.blizzard.models.profile import ProfileLadderResponse
from backend.db.model import Character, Ladder
from backend.etl.execution import conclude_etl_execution, initiate_etl_execution
from backend.static import (
    BLIZZARD_503_RETRY_MAX,
    LADDER_CHARACTER_MMR_LOOKUP_KEY,
    LADDER_RESULTS_JOB_NAME,
    MMR_MAX,
    MMR_MIN,
)
from backend.utils.concurrency import yield_futures
from backend.utils.datetime import current_epoch_time, datetime_to_epoch
from backend.utils.log import get_logger

# TODO refactor this ETL for team types beyond 1v1

logger = get_logger(__name__)


class MissingCharacter(Exception):
    pass


class TooManyCharacters(Exception):
    pass


def get_profile_ladder_wrapper(ladder_member):
    api = BlizzardApi()
    return ProfileLadderResponse.model_validate(
        api.get_profile_ladder(
            region_id=ladder_member.get("region_id"),
            realm_id=ladder_member.get("realm_id"),
            profile_id=ladder_member.get("profile_id"),
            ladder_id=ladder_member.get("ladder_id"),
        )
    )


def fetch_profile_ladder(region_id):
    # Query for all ladders in given region for current season
    blizzard_api = BlizzardApi()
    season = SeasonResponse.model_validate(blizzard_api.get_ladder_season(region_id=region_id))
    ladders = [
        Ladder(**ladder)
        for ladder in SC2StatsAPI.get(
            endpoint=f"/ladder/{season.season_id}/{region_id}",
        ).get("results")
    ]

    # Create a map of ladders --> ladder_members (join on ladder_member / profile)
    ladder_members_lookup = defaultdict(list)
    for ladder in ladders:
        ladder_members_lookup[ladder.id] = SC2StatsAPI.get(
            endpoint=f"/ladder_member/{ladder.id}",
        ).get(
            "results"
        )[0:BLIZZARD_503_RETRY_MAX]

    # Fetch ladder results.
    # For each ladder we use a ladder_member to hit /sc2/profile/:regionId/:realmId/:profileId/ladder/:ladderId
    # At time of writing this endpoint is wildly sporadic. On failure it returns 503, sometimes 500.
    # To mitigate this we attempt to get ladder results by using multiple ladder members.
    # There is a decreased request timeout for these GET requests. 503 would just hang before returning (5+ sec).
    iteration = 0
    responses = []
    logger.info(f"Starting fetch of ladder results. {region_id=}")
    while ladder_members_lookup and iteration < BLIZZARD_503_RETRY_MAX:
        logger.info(f"Will attempt fetch for {len(ladder_members_lookup)} ladders. {iteration=}, {region_id=}")
        ladder_members = [members[0] for members in ladder_members_lookup.values() if len(members) > 0]
        future_results = list(yield_futures(get_profile_ladder_wrapper, ladder_members))
        for response, ladder_member in future_results:
            if response.ladder_teams and len(response.ladder_teams) > 0:
                # If we got a response with ladder_teams, remove from dict to prevent processing in future iterations.
                del ladder_members_lookup[ladder_member["pkey_ladder_id"]]
                response.ladder_member = ladder_member
                responses.append(response)

        logger.info(f"Done with ladder results iteration. {iteration=}, {region_id=}")
        iteration += 1

        # Purge the member that was used in failed fetch
        for members in ladder_members_lookup.values():
            if members:
                members.pop(0)

    logger.info(
        f"Could not get results for {len(ladder_members_lookup)}/{len(ladders)} ladders."
        f"ladder_ids={ladder_members_lookup.keys()}"
    )
    logger.info(f"Done fetch of ladder results. Returning {len(responses)} valid responses.")
    return responses


def get_ladder_results(**kwargs):
    logger.info("Starting fetch of ladder results...")
    start = datetime.now()

    region_id = kwargs.get("region_id")
    if not region_id:
        logger.warning("Missing required param region_id")
        return

    etl_execution = initiate_etl_execution(
        name=LADDER_RESULTS_JOB_NAME, region_id=region_id, start_timestamp=datetime_to_epoch(start)
    )

    matches = []
    character_mmrs = []
    responses = fetch_profile_ladder(region_id=region_id)
    for result, _ in yield_futures(process_profile_ladder_response, responses):
        matches = matches + result[0]
        character_mmrs = character_mmrs + result[1]

    if matches:
        logger.info(f"Inserting matches. {region_id=}")
        SC2StatsAPI.post(
            endpoint="/post/match",
            data={"rows": matches},
        )

    if character_mmrs:
        logger.info(f"Inserting characterMMRs. {region_id=}")
        SC2StatsAPI.post(
            endpoint="/post/character_mmr",
            data={"rows": character_mmrs},
        )

    end = datetime.now()
    conclude_etl_execution(etl_execution, end_timestamp=datetime_to_epoch(end))
    logger.info(f"Processed a total of {len(responses)} ladders.")
    logger.info(f"Processing ladder results took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with fetch of ladder results.")


def process_profile_ladder_response(response):
    matches = []
    character_mmrs = []

    # Fetch latest MMRs in PG for given ladder
    ladder_character_mmrs = SC2StatsAPI.get(
        endpoint=f"/ladder/character_mmr/{response.ladder_member["pkey_ladder_id"]}",
    ).get("results")

    for ladder_team in response.ladder_teams:
        if not ladder_team.mmr:
            continue

        if ladder_team.mmr < MMR_MIN or ladder_team.mmr > MMR_MAX:
            logger.warning(f"The following LadderTeam has an invalid MMR and will not be processed: {ladder_team}")
            continue

        for team_member in ladder_team.team_members:
            if (
                not team_member.profile_id
                or not team_member.realm_id
                or not team_member.region_id
                or not team_member.display_name
                or not team_member.race
            ):
                logger.warning(
                    f"The following TeamMember is missing required attrs and will not be processed: {team_member}"
                )
                continue

            lookup_key = LADDER_CHARACTER_MMR_LOOKUP_KEY.format(
                profile_id=team_member.profile_id,
                realm_id=team_member.realm_id,
                region_id=team_member.region_id,
                display_name=team_member.display_name,
                race=team_member.race.value,
            )

            ladder_mmr = ladder_team.mmr
            db_mmr = None
            if lookup_key in ladder_character_mmrs:
                # We have a prior mmr entry for ladder_member
                lader_character_mmr = ladder_character_mmrs[lookup_key]
                db_mmr = lader_character_mmr.get("mmr")
                if db_mmr == ladder_mmr:
                    continue

                matches.append(
                    {
                        "end_timestamp": current_epoch_time(),
                        "profile_id": lader_character_mmr.get("pkey_profile_id"),
                    }
                )

            else:
                try:
                    character = Character(
                        **one(
                            SC2StatsAPI.get(
                                endpoint=f"/character/{team_member.region_id}/{team_member.realm_id}/"
                                + f"{team_member.profile_id}/{team_member.display_name}",
                            ).get("results"),
                            too_short=MissingCharacter,
                            too_long=TooManyCharacters,
                        )
                    )
                except MissingCharacter:
                    logger.warning(f"Missing character. Likely resolved with next fetch of ladders. {lookup_key=}")
                    continue
                except TooManyCharacters:
                    logger.warning(f"Too many characters. {lookup_key=}")
                    continue

            logger.debug(
                f"New MMR result for {team_member.profile_id}:{team_member.display_name}:{team_member.race} "
                + f"{db_mmr} --> {ladder_mmr}"
            )

            character_mmrs.append(
                {
                    "race": team_member.race.value,
                    "mmr": ladder_team.mmr,
                    "date": current_epoch_time(),
                    "character_id": (
                        lader_character_mmr.get("pkey_character_id")
                        if lookup_key in ladder_character_mmrs
                        else character.id
                    ),
                }
            )
    return (matches, character_mmrs)
