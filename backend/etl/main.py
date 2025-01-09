import argparse
import time

import schedule
from dotenv import load_dotenv

from backend.api.blizzard import reset_day_request_count, reset_second_request_count
from backend.etl.game import create_games
from backend.etl.ladder import get_ladders
from backend.etl.ladder_member import get_ladder_members
from backend.etl.ladder_result import get_ladder_results
from backend.utils.concurrency_utils import run_threaded
from backend.utils.logging_utils import get_logger

load_dotenv()

logger = get_logger(__name__)


def handle_schedule():
    logger.info("Scheduling all jobs...")
    schedule.every(5).minutes.do(run_threaded, get_ladders)
    schedule.every(5).minutes.do(run_threaded, get_ladder_members)
    schedule.every(30).seconds.do(run_threaded, get_ladder_results)
    schedule.every(5).minutes.do(run_threaded, create_games)

    while all(True):
        schedule.run_pending()
        time.sleep(1)


def handle_process(process):
    threads = []
    if process:
        logger.info(f"Starting single execution of {process=}")
        if process == "ladder":
            threads.append(run_threaded(get_ladders))
        if process == "ladder_members":
            threads.append(run_threaded(get_ladder_members))
        elif process == "ladder_results":
            threads.append(run_threaded(get_ladder_results))
        elif process == "games":
            threads.append(run_threaded(create_games))
        elif process == "all":
            threads.append(run_threaded(get_ladders))
            threads.append(run_threaded(get_ladder_members))
            threads.append(run_threaded(get_ladder_results))
            threads.append(run_threaded(create_games))
        else:
            logger.error(f"Unable to execute {process=}")

    while all(threads):
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--process")
    parser.add_argument("-s", "--schedule", action="store_true")
    args = parser.parse_args()

    schedule.every(1).second.do(run_threaded, reset_second_request_count)
    schedule.every(1).day.do(run_threaded, reset_day_request_count)

    if args.schedule:
        handle_schedule()
    elif args.process:
        handle_process(args.process)
    else:
        logger.error("Missing required argument.")
