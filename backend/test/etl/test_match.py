from enum import Enum

from backend.blizzard.models.legacy import Match as LadderMatch
from backend.db.model import Match
from backend.enums import MatchDecision, MatchSpeed, MatchType
from backend.etl.match import get_matches
from backend.test.helper import TestCaseBase


class MapName(Enum):
    NVSLE = "Neon Violet Square LE"
    LL = "Ley Lines"
    RBLE = "Abyssal Reef LE"


MOCK_PROFILE_ID = 1
BASE_START_TIMESTAMP = 1737100000
BASE_MATCH_DURATION = 60 * 5


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


class TestMatchETL(TestCaseBase):
    def setUp(self):
        super().setUp()

        self.monkeypatch.setattr(
            "backend.etl.match.fetch_matches",
            lambda _: (
                {
                    1: [
                        _ladder_match(
                            map=MapName.NVSLE.value,
                            type=MatchType._1V1.value,
                            decision=MatchDecision.LOSS.value,
                            speed=MatchSpeed.FASTER.value,
                            date=BASE_START_TIMESTAMP,
                        )
                    ]
                },
                {
                    1: [
                        _db_match(
                            1,
                            BASE_START_TIMESTAMP + BASE_MATCH_DURATION,
                            False,
                        )
                    ]
                },
            ),
        )

    def test_match_etl(self):
        """Happy path"""
        get_matches(**{"region_id": 2})
