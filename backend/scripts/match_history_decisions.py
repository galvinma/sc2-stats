"""
Scrape match histories to determine possible values for decision field

docker compose run --remove-orphans \
    -v $PWD/backend:/app/backend \
    -v $PWD/notes/match_history:/app/notes/match_history \
    sc2-stats-etl python -m backend.scripts.match_history_decisions

---

decisions={'Win', 'Tie', 'Loss', 'Observer', 'Left'}
"""

import json

from dotenv import load_dotenv

from backend.api.methods import SC2StatsAPI
from backend.blizzard.api import BlizzardApi
from backend.blizzard.models.ladder import SeasonResponse
from backend.blizzard.models.legacy import LegacyMatchHistoryResponse
from backend.db.model import Ladder

load_dotenv()


region_id = 2


def get_match_history_wrapper(profile):
    api = BlizzardApi()
    return LegacyMatchHistoryResponse.model_validate(
        api.get_legacy_match_history(
            region_id=profile.get("region_id"),
            realm_id=profile.get("realm_id"),
            profile_id=profile.get("profile_id"),
        )
    )


blizzard_api = BlizzardApi()
season = SeasonResponse.model_validate(blizzard_api.get_ladder_season(region_id=region_id))
ladders = [
    Ladder(**ladder)
    for ladder in SC2StatsAPI.get(
        endpoint=f"/ladder/{season.season_id}/{region_id}",
    ).get("results")
]

profiles = []
for ladder in ladders:
    profiles = profiles + SC2StatsAPI.get(
        endpoint=f"/ladder_member/{ladder.id}",
    ).get("results")

decisions = set()
processed = 0
for profile in profiles:
    match_history_response = get_match_history_wrapper(profile)
    if match_history_response and match_history_response.matches:
        for match in match_history_response.matches:
            decisions.add(match.decision)

        f_name = (
            f"{profile.get("ladder_id")}_{profile.get("profile_id")}"
            + f"_{profile.get("realm_id")}_{profile.get("region_id")}"
        )
        with open(f"/app/notes/match_history/{f_name}.json", "w", encoding="utf-8") as f:
            json.dump(match_history_response.model_dump(), f, ensure_ascii=False, indent=4)

    if processed != 0 and processed % 25 == 0:
        print(f"Processed {processed} profiles...")
        print(f"{decisions=}")

    processed += 1
