"""
ETL processes associated with SC2 ladder members (Profile/Character)
"""

import time
from datetime import datetime

from backend.api.methods import SC2StatsAPI
from backend.blizzard.api import BlizzardApi
from backend.blizzard.models.ladder import SeasonResponse
from backend.blizzard.models.legacy import LegacyLadderResponse
from backend.db.model import Ladder, Profile
from backend.static import LADDER_BATCH_SIZE
from backend.utils.concurrency import yield_futures
from backend.utils.log import get_logger

logger = get_logger(__name__)


def get_legacy_ladder_wrapper(ladder):
    api = BlizzardApi()
    return LegacyLadderResponse.model_validate(
        api.get_legacy_ladder(region_id=ladder.region_id, ladder_id=ladder.ladder_id)
    )


def fetch_ladders(region_id):
    processed = 0
    batch_start = time.time()
    blizzard_api = BlizzardApi()
    season = SeasonResponse.model_validate(blizzard_api.get_ladder_season(region_id=region_id))
    ladders = [
        Ladder(**ladder)
        for ladder in SC2StatsAPI.get(
            endpoint=f"/ladder/{season.season_id}/{region_id}",
        ).get("results")
    ]

    for result, ladder_future in yield_futures(func=get_legacy_ladder_wrapper, iterable=ladders):
        if processed != 0 and processed % LADDER_BATCH_SIZE == 0:
            logger.info(
                f"Have fetched {processed} ladders. "
                f"Last batch took {round(time.time() - batch_start)} seconds. {region_id=}"
            )
            batch_start = time.time()

        result.ladder_id = ladder_future.id
        yield result
        processed += 1
    logger.info(f"Done with fetch of ladders. Fetched {processed} total ladders. {region_id=}")


def get_ladder_members(**kwargs):
    logger.info("Starting fetch of ladder members (characters)...")
    start = datetime.now()
    processed_ladders = 0
    profiles = []
    characters = []
    ladder_members = []
    spent_characters = set()
    spent_ladder_members = set()

    region_id = kwargs.get("region_id")
    if not region_id:
        logger.warning("Missing required param region_id")
        return

    # Process ladder responses and parse out profiles
    # It is more efficient to iterate multiple time and bulk upsert than to constantly ping the DB
    responses = []
    for ladder_response in fetch_ladders(region_id=region_id):
        responses.append(ladder_response)
        logger.info(f"Got response for ladder {ladder_response.ladder_id}...")
        for ladder_member in ladder_response.ladder_members:
            profiles.append(
                {
                    "profile_id": ladder_member.character.profile_id,
                    "realm_id": ladder_member.character.realm_id,
                    "region_id": ladder_member.character.region_id,
                }
            )
        processed_ladders += 1

    logger.info(f"Parsed {len(profiles)} profiles from {processed_ladders} ladders. {region_id=}")

    # Commit the profiles
    SC2StatsAPI.put(
        endpoint="/put/profile",
        data={"rows": profiles},
    )
    profiles = [
        Profile(**profile)
        for profile in SC2StatsAPI.get(endpoint="/get/profile", params={"region_id": region_id}).get("results")
    ]

    # Create a lookup of profiles for character and ladder_member insertion
    profile_lookup_key = "{profile_id}_{realm_id}_{region_id}"
    profile_lookup = {}
    for profile in profiles:
        lookup_key = profile_lookup_key.format(
            profile_id=profile.profile_id, realm_id=profile.realm_id, region_id=profile.region_id
        )
        profile_lookup[lookup_key] = profile

    # Process ladder responses and parse out characters and ladder_members
    for response in responses:
        for ladder_member in response.ladder_members:
            if (
                not ladder_member.character.profile_id
                or not ladder_member.character.realm_id
                or not ladder_member.character.region_id
                or not ladder_member.character.display_name
            ):
                logger.warning(
                    f"The following LadderMember is missing required attrs and will not be saved: {ladder_member}"
                )
                continue

            profile = profile_lookup[
                profile_lookup_key.format(
                    profile_id=ladder_member.character.profile_id,
                    realm_id=ladder_member.character.realm_id,
                    region_id=ladder_member.character.region_id,
                )
            ]

            character_lookup_key = f"{profile.id}_{ladder_member.character.display_name}"
            if character_lookup_key not in spent_characters:
                characters.append(
                    {
                        "display_name": ladder_member.character.display_name,
                        "clan_name": ladder_member.character.clan_name,
                        "clan_tag": ladder_member.character.clan_tag,
                        "profile_path": ladder_member.character.profile_path,
                        "profile_id": profile.id,
                    }
                )
                spent_characters.add(character_lookup_key)

            ladder_member_lookup_key = (
                f"{ladder_member.character.profile_id}_{response.ladder_id}_{ladder_member.join_timestamp}"
            )
            if ladder_member_lookup_key not in spent_ladder_members:
                ladder_member = {
                    "join_timestamp": ladder_member.join_timestamp,
                    "points": ladder_member.points,
                    "wins": ladder_member.wins,
                    "losses": ladder_member.losses,
                    "highest_rank": ladder_member.highest_rank,
                    "previous_rank": ladder_member.previous_rank,
                    "race": ladder_member.race,
                    "profile_id": profile.id,
                    "ladder_id": response.ladder_id,
                }

                ladder_members.append(ladder_member)
                spent_ladder_members.add(ladder_member_lookup_key)

    # Bulk upsert of characters and ladder_members
    logger.info(f"Upserting characters. {region_id=}")
    SC2StatsAPI.put(
        endpoint="/put/character",
        data={"rows": characters, "set_": ["clan_name", "clan_tag"]},
    )

    logger.info(f"Upserting ladder members. {region_id=}")
    SC2StatsAPI.put(
        endpoint="/put/ladder_member",
        data={"rows": ladder_members, "set_": ["points", "wins", "losses", "highest_rank", "previous_rank"]},
    )

    end = datetime.now()
    logger.info(f"Processing ladder members took {round(end.timestamp() - start.timestamp())} seconds. ({region_id=})")
    logger.info(f"Done with fetch of ladder members. {region_id=} ")
