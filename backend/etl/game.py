"""
ETL processes associated with SC2 ladder games
"""

from collections import defaultdict
from datetime import datetime, timedelta

from backend.db.db import get_or_create, query, session_scope
from backend.db.model import Game, Match
from backend.static import MATCH_LOOKBACK_MAX, MATCH_LOOKBACK_MIN, MATCH_LOOKUP_KEY
from backend.utils.datetime import datetime_to_epoch
from backend.utils.log import get_logger

# TODO refactor pairing logic to support game modes other than 1V1


logger = get_logger(__name__)


def query_unpaired_matches(session):
    """Get all matches in recent history that have not been merged into a game"""

    lookback_max = datetime_to_epoch(datetime.now() - timedelta(0, MATCH_LOOKBACK_MAX))
    lookback_min = datetime_to_epoch(datetime.now() - timedelta(0, MATCH_LOOKBACK_MIN))
    return query(
        session,
        params={Match},
        filters=[(Match.game_id == None), (Match.date > lookback_max), (Match.date < lookback_min)],  # noqa E711
    )


def insert_game(session, matches):
    durations = [match.duration for match in matches if match.duration is not None]
    duration_average = sum(durations) / len(durations) if durations else None
    game = get_or_create(session, model=Game, values={"duration": duration_average}, filter={})
    for match in matches:
        match.game_id = game.id
        match.game = game
        session.add(match)
    session.commit()


def pair_matches():

    lookup = defaultdict(list)
    with session_scope() as session:
        matches = query_unpaired_matches(session)
        logger.info(f"Found {len(matches)} unpaired recent matches...")
        for match in matches:
            key = MATCH_LOOKUP_KEY.format(map=match.map, type=match.type, date=match.date, speed=match.speed)
            lookup[key].append(match)

        waiting_pair = 0
        paired = 0
        conflict = 0
        for _, matches in lookup.items():
            if not matches or len(matches) < 1:
                continue

            if len(matches) == 1:
                waiting_pair += len(matches)
                continue

            if len(matches) > 2:
                conflict += len(matches)
                continue

            if len(matches) == 2:
                # TODO Validate number of wins/losses
                paired += 1
                insert_game(session, matches)

    logger.info(f"Paired {paired} matches.")
    logger.info(f"{waiting_pair} matches still waiting for results.")
    logger.info(f"{conflict} matches have a pairing conflict.")


def create_games():
    logger.info("Starting analysis of recent matches. Will attempt to merge matches into games...")
    start = datetime.now()
    pair_matches()
    end = datetime.now()
    logger.info(f"Processing recent matches took {round(end.timestamp() - start.timestamp())} seconds.")
    logger.info("Done with analysis of recent matches.")
