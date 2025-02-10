from enum import Enum

from backend.blizzard.models.legacy import Match as LadderMatch
from backend.db.model import Match
from backend.enums import MatchDecision, MatchSpeed, MatchType
from backend.etl.match import ReconcileFuture
from backend.etl.transform.match import reconcile_matches

MOCK_PROFILE_ID = 1
BASE_START_TIMESTAMP = 1737100000
BASE_MATCH_DURATION = 60 * 5


class MapName(Enum):
    NVSLE = "Neon Violet Square LE"
    LL = "Ley Lines"
    RBLE = "Abyssal Reef LE"


def test_reconcile_matches_no_matches():
    """No exception when passing no matches"""
    upsert, remove = reconcile_matches(ReconcileFuture(profile_id=MOCK_PROFILE_ID, ladder_matches=[], db_matches=[]))
    for arr in [upsert, remove]:
        assert not arr


def test_reconcile_matches_ladder_only():
    """Upsert when passed ladder matches, but zero db matches"""
    ladder_matches = [
        _ladder_match(
            map=MapName.NVSLE.value,
            type=MatchType._1V1.value,
            decision=MatchDecision.LOSS.value,
            speed=MatchSpeed.FASTER.value,
            date=BASE_START_TIMESTAMP,
        )
    ]
    upsert, remove = reconcile_matches(
        ReconcileFuture(profile_id=MOCK_PROFILE_ID, ladder_matches=ladder_matches, db_matches=[])
    )
    assert not remove
    assert upsert == [
        _strip_ids(
            _db_match(
                profile_id=MOCK_PROFILE_ID,
                map=MapName.NVSLE.value,
                type=MatchType._1V1.value,
                decision=MatchDecision.LOSS.value,
                speed=MatchSpeed.FASTER.value,
                start_timestamp=BASE_START_TIMESTAMP,
                end_timestamp=None,
                duration=None,
                reconciled=True,
            ).as_dict()
        )
    ]


def test_reconcile_matches_happy_path_one_match():
    """Can reconcile one ladder match to one db match"""
    ladder_matches = [
        _ladder_match(
            map=MapName.NVSLE.value,
            type=MatchType._1V1.value,
            decision=MatchDecision.LOSS.value,
            speed=MatchSpeed.FASTER.value,
            date=BASE_START_TIMESTAMP,
        )
    ]
    db_matches = [
        _db_match(
            profile_id=MOCK_PROFILE_ID,
            end_timestamp=BASE_START_TIMESTAMP + BASE_MATCH_DURATION,
            decision=MatchDecision.LOSS.value,
            reconciled=False,
        )
    ]
    upsert, remove = reconcile_matches(
        ReconcileFuture(profile_id=MOCK_PROFILE_ID, ladder_matches=ladder_matches, db_matches=db_matches)
    )
    assert not remove
    assert upsert == [
        _db_match(
            profile_id=MOCK_PROFILE_ID,
            map=MapName.NVSLE.value,
            type=MatchType._1V1.value,
            decision=MatchDecision.LOSS.value,
            speed=MatchSpeed.FASTER.value,
            start_timestamp=BASE_START_TIMESTAMP,
            end_timestamp=BASE_START_TIMESTAMP + BASE_MATCH_DURATION,
            duration=BASE_MATCH_DURATION,
            reconciled=True,
        ).as_dict()
    ]


def _ladder_match(map, type, decision, speed, date):
    return LadderMatch(map=map, type=type, decision=decision, speed=speed, date=date)


def _db_match(
    profile_id,
    end_timestamp,
    reconciled,
    map=None,
    type=None,
    decision=None,
    speed=None,
    start_timestamp=None,
    duration=None,
):
    return Match(
        profile_id=profile_id,
        map=map,
        type=type,
        decision=decision,
        speed=speed,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        duration=duration,
        reconciled=reconciled,
    )


def _strip_ids(match):
    if "id" in match:
        del match["id"]

    if "game_id" in match:
        del match["game_id"]

    return match
