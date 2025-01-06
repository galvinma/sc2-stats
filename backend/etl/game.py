"""
ETL processes associated with SC2 ladder games
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from backend.db.db import Session, insert, query
from backend.db.model import Game, Match
from backend.static import MATCH_LOOKBACK_MAX, MATCH_LOOKBACK_MIN, MATCH_LOOKUP_KEY
from backend.utils.datetime_utils import datetime_to_epoch

# TODO refactor pairing logic to support game modes other than 1V1


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
    game = insert(
        session,
        model=Game,
        values={"duration": duration_average},
    )
    for match in matches:
        match.game_id = game.id
        match.game = game
        session.add(match)
    session.commit()


def pair_matches():

    lookup = defaultdict(list)
    with Session() as session:
        matches = query_unpaired_matches(session)
        logging.info(f"Found {len(matches)} unpaired recent matches...")
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
            paired += 1
            insert_game(session, matches)

    logging.info(f"Paired {paired} matches.")
    logging.info(f"{waiting_pair} matches still waiting for results.")
    logging.info(f"{conflict} matches have a pairing conflict.")


def create_games():
    logging.info("Starting analysis of recent matches. Will attempt to merge matches into games...")
    start = datetime.now()
    pair_matches()
    end = datetime.now()
    logging.info(f"Processing recent matches took {round(end.timestamp() - start.timestamp())} seconds.")
