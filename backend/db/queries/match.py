from backend.db.db import query
from backend.db.model import Match, Profile


def query_unreconciled_matches(region_id):
    return [
        obj.as_dict()
        for obj in query(
            params={Match},
            joins=[(Profile, Profile.id == Match.profile_id)],
            filters=[
                (Match.reconciled == False),  # noqa E711
                (Profile.region_id == region_id),
            ],
        )
    ]


def query_profile_matches(region_id, profile_id):
    return [
        obj.as_dict()
        for obj in query(
            params={Match},
            joins=[(Profile, Profile.id == Match.profile_id)],
            filters=[
                (Profile.id == profile_id),
                (Profile.region_id == region_id),
            ],
        )
    ]
