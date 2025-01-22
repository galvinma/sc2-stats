from backend.db.db import query
from backend.db.model import (
    Character,
    CharacterMMR,
    ETLExecution,
    Ladder,
    LadderMember,
    League,
    Profile,
)
from backend.static import LADDER_CHARACTER_MMR_LOOKUP_KEY
from backend.utils.log import get_logger

logger = get_logger(__name__)


def query_most_recent_etl_execution(name, region_id):
    """Return most recent ETL execution for given name and region_id"""
    return [
        obj.as_dict()
        for obj in query(
            params={ETLExecution},
            filters=[
                (ETLExecution.name == name),
                (ETLExecution.region_id == region_id),
            ],
            order_by=[ETLExecution.start_timestamp.desc()],
            limit=1,
        )
    ]


def query_ladders(season_id, region_id):
    """Retrieve ladders associated with given season and region."""
    return [
        obj.as_dict()
        for obj in query(
            params={Ladder},
            joins=[(League, League.id == Ladder.league_id)],
            filters=[(Ladder.region_id == region_id), (League.season_id == season_id)],
        )
    ]


def query_ladder_members(ladder_id):
    """Retrieve combined profile/ladder_member object associated with given ladder."""
    return [
        row._asdict()
        for row in query(
            params={
                LadderMember.id,
                Ladder.id.label("pkey_ladder_id"),
                Ladder.ladder_id,
                Profile.id.label("pkey_profile_id"),
                Profile.region_id,
                Profile.realm_id,
                Profile.profile_id,
            },
            joins=[
                (Profile, Profile.id == LadderMember.profile_id),
                (Ladder, Ladder.id == LadderMember.ladder_id),
            ],
            filters=[(Ladder.id == ladder_id)],
        )
    ]


def query_ladder_character_mmrs(pkey_ladder_id):
    """Retrieve most recent character_mmrs for a given ladder"""
    rows = [
        row._asdict()
        for row in query(
            params={
                CharacterMMR.date,
                CharacterMMR.race,
                CharacterMMR.mmr,
                Character.display_name,
                Profile.profile_id,
                Profile.realm_id,
                Profile.region_id,
                LadderMember.id.label("pkey_ladder_member_id"),
                CharacterMMR.id.label("pkey_character_mmr_id"),
                Character.id.label("pkey_character_id"),
                Profile.id.label("pkey_profile_id"),
            },
            joins=[
                (Profile, Profile.id == LadderMember.profile_id),
                (Character, Character.profile_id == LadderMember.profile_id),
                (CharacterMMR, CharacterMMR.character_id == Character.id),
            ],
            filters=[
                (LadderMember.ladder_id == pkey_ladder_id),
            ],
            order_by=[CharacterMMR.date.desc()],
        )
    ]

    # TODO conduct filtering in the query. Was struggling to combine DISTINCT & ORDER BY
    #   Think I just need a subquery.

    res = {}
    spent = set()
    for row in rows:
        lookup_key = LADDER_CHARACTER_MMR_LOOKUP_KEY.format(
            profile_id=row.get("profile_id"),
            realm_id=row.get("realm_id"),
            region_id=row.get("region_id"),
            display_name=row.get("display_name"),
            race=row.get("race").value,
        )
        if lookup_key not in spent:
            spent.add(lookup_key)
            res[lookup_key] = row

    return res


def query_character(region_id, realm_id, profile_id, display_name):
    return [
        obj.as_dict()
        for obj in query(
            params={Character},
            joins=[(Profile, Profile.id == Character.profile_id)],
            filters=[
                (Profile.profile_id == profile_id),
                (Profile.realm_id == realm_id),
                (Profile.region_id == region_id),
                (Character.display_name == display_name),
            ],
        )
    ]
