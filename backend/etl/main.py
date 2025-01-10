import argparse
import time

import schedule
from dotenv import load_dotenv

from backend.etl.game import create_games
from backend.etl.ladder import get_ladders
from backend.etl.ladder_member import get_ladder_members
from backend.etl.ladder_result import get_ladder_results
from backend.utils.concurrency import run_threaded
from backend.utils.log import get_logger
from backend.utils.state import AppState

load_dotenv()

logger = get_logger(__name__)


def handle_schedule():
    logger.info("Scheduling all jobs...")
    schedule.every(30).seconds.do(run_threaded, get_ladders)
    schedule.every(45).seconds.do(run_threaded, get_ladder_members)
    schedule.every(90).seconds.do(run_threaded, get_ladder_results)
    schedule.every(60).seconds.do(run_threaded, create_games)

    while True:
        schedule.run_pending()
        time.sleep(1)


def handle_process(process):
    threads = []

    logger.info(f"Starting single execution of {process=}")
    if process == "ladder":
        threads.append(run_threaded(get_ladders))
    elif process == "ladder_members":
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

    while all([thread.is_alive() for thread in threads]):
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--process")
    parser.add_argument("-s", "--schedule", action="store_true")
    args = parser.parse_args()

    schedule.every(1).second.do(run_threaded, AppState.reset_second_request_count)
    schedule.every(1).day.do(run_threaded, AppState.reset_day_request_count)
    schedule.every(10).seconds.do(run_threaded, AppState.log_app_state)

    if args.schedule:
        handle_schedule()
    elif args.process:
        handle_process(args.process)
    else:
        logger.error("Missing required argument.")
