from backend.enums import MatchDecision
from backend.static import MATCH_RECONCILE_LOOKUP_KEY
from backend.utils.log import get_logger

logger = get_logger(__name__)


def reconcile_matches(reconcile_future):
    """
    Attempt to pair blizzard API ladder matches with matches in the DB.

    We know a match has been played by constantly polling the ladder members API and detecting MMR changes.

    At that moment we create a match 'shell' which contains:
        1. profile_id, int
        2. ~end_timestamp, int, Used to calculate match duration.
        3. reconciled, bool, Indicates the match has NOT been reconciled with blizzard match API.
        4. decision, string, match result. Only included if possible to determine from MMR delta.


    If there are zero DB matches, just insert all matches from blizzard response.


    - Establish start timestamp of oldest blizzard match. Remove anything from DB matches older than that date.
    - Iterate through the blizzard matches. Pair with reconciled DB matches and remove from lists.
    - Iterate through the blizzard matches that are left.
        - Attempt to pair oldest start_timestamp of blizzard match with oldest end_timestamp of DB matches.
        - Verify decision matches and end_timestamp > start_timestamp.
        - If lists are same length && matches pass verification, mark reconciled.
        - If there are more blizzard than DB matches we have missed match(es)
            - If it's just one match, do nothing. Assume the ladder_results ETL will
                detect the MMR change and make a match shell.
            - If it's multiple,

        - If there are more DB matches than blizzard matches, assume error. Remove extra DM matches

    """
    profile_id = reconcile_future.profile_id
    ladder_matches = reconcile_future.ladder_matches
    db_matches = reconcile_future.db_matches

    delete = []
    upsert = []
    if not profile_id:
        logger.warning(f"Profile Id is required to reconcile matches. {profile_id=}.")
        return [], []

    if not ladder_matches:
        logger.warning(f"Cannot reconcile because missing ladder matches. {profile_id=}.")
        return [], []

    logger.info(f"Starting match reconciliation for {profile_id=}.")
    logger.info(f"Received {len(ladder_matches)} API match(es) and {len(db_matches)} DB match(es). {profile_id=}")

    # Filter out old DB matches
    oldest_start_timestamp = min(match.start_timestamp for match in ladder_matches)
    logger.debug(f"Filtering out DB matches older than {oldest_start_timestamp}.")
    db_matches = [
        match
        for match in db_matches
        if (match.end_timestamp and match.end_timestamp > oldest_start_timestamp)
        or (match.start_timestamp and match.start_timestamp > oldest_start_timestamp)
    ]

    # Create lookup to link ladder matches to reconciled db matches
    reconciled_lookup = {}
    for match in db_matches:
        if match.reconciled:
            lookup_key = MATCH_RECONCILE_LOOKUP_KEY.format(
                map=match.map,
                type=match.type,
                speed=match.speed,
                decision=match.decision,
                start_timestamp=match.start_timestamp,
            )
            reconciled_lookup[lookup_key] = match

    # Filter out ladder matches that map to reconciled db matches
    ladder_matches = [
        match
        for match in ladder_matches
        if MATCH_RECONCILE_LOOKUP_KEY.format(
            map=match.map,
            type=match.type,
            speed=match.speed,
            decision=match.decision,
            start_timestamp=match.start_timestamp,
        )
        not in reconciled_lookup
    ]

    # Filter out reconciled db matches
    db_matches = [match for match in db_matches if not match.reconciled]

    logger.info(
        "After filtering out reconciled matches there are "
        + f"{len(ladder_matches)} API matches and {len(db_matches)} DB matches."
    )

    if not ladder_matches and not db_matches:
        return []

    if len(db_matches) < len(ladder_matches):
        logger.info(
            "More API matches than DB matches. Will delete unreconciled DB matches and "
            + "take ladder matches as truth."
        )
        # We have missed insertion of at least one DB match.
        # This could be due to ETL downtime, poor ETL timing, or an error.
        # Take ladder matches as truth
        delete += db_matches
        for match in ladder_matches:
            match = _db_match(
                profile_id=profile_id,
                map=match.map,
                type=match.type,
                speed=match.speed,
                decision=match.decision,
                start_timestamp=match.start_timestamp,
                reconciled=True,
            )
            match = dict(sorted(match.items()))
            upsert.append(match)
    elif len(db_matches) > len(ladder_matches):
        logger.info("Found more DB matches than API matches.")

        # The Blizzard match API and the ladder API are out of sync
        # If delta is more than one, assume something went wrong and purge db matches
        # Else, assume that Blizzard API will catch up and we will reconcile this match later
        if len(db_matches) - len(ladder_matches) != 1:
            logger.info("More than one mismatch. Purging unreconciled DB matches.")
            delete += db_matches
    else:
        logger.info("Attempting to reconcile matches.")
        ladder_matches = sorted(ladder_matches, key=lambda match: match.start_timestamp)
        db_matches = sorted(db_matches, key=lambda match: match.end_timestamp)
        reconciled_matches = []
        can_reconcile = True

        for ladder_match, db_match in zip(ladder_matches, db_matches):
            if _can_reconcile(ladder_match=ladder_match, db_match=db_match):
                reconciled_match = db_match.as_dict() | {
                    "map": ladder_match.map,
                    "type": ladder_match.type,
                    "decision": ladder_match.decision,
                    "speed": ladder_match.speed,
                    "start_timestamp": ladder_match.start_timestamp,
                    "duration": db_match.end_timestamp - ladder_match.start_timestamp,
                    "reconciled": True,
                }
                reconciled_match = dict(sorted(reconciled_match.items()))
                logger.debug(f"{reconciled_match=}")
                reconciled_matches.append(reconciled_match)
            else:
                can_reconcile = False

        if can_reconcile:
            logger.info(f"Reconciled {len(reconciled_matches)} matches. {profile_id=}")
            upsert += reconciled_matches
        else:
            logger.info(f"Failed to reconcile matches. {profile_id=}")
            # logger.info(f"{ladder_matches=}")
            # logger.info(f"{db_matches=}")

    return upsert, delete


def _db_match(
    profile_id, map, type, decision, speed, start_timestamp, end_timestamp=None, duration=None, reconciled=False
):
    return {
        "profile_id": profile_id,
        "map": map,
        "type": type,
        "decision": decision,
        "speed": speed,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "duration": duration,
        "reconciled": reconciled,
    }


def _can_reconcile(ladder_match, db_match):
    """Determine if a ladder_match and db_match are possible to reconcile"""

    if db_match.reconciled:
        return False

    if ladder_match.start_timestamp > db_match.end_timestamp:
        return False

    if (
        db_match.decision in [MatchDecision.LOSS.value, MatchDecision.WIN.value]
        and db_match.decision != ladder_match.decision
    ):
        return False

    return True
