import argparse
import time

import schedule
from dotenv import load_dotenv

from backend.enums import RegionId
from backend.etl.ladder import get_ladders
from backend.etl.ladder_member import get_ladder_members
from backend.etl.ladder_result import get_ladder_results

# from backend.etl.match import create_games
from backend.etl.match import get_matches
from backend.etl.state import log_app_state
from backend.utils.concurrency import run_threaded
from backend.utils.log import get_logger

load_dotenv()

logger = get_logger(__name__)


def handle_schedule():
    logger.info("Scheduling all jobs...")

    schedule.every(10).seconds.do(job_func=run_threaded, kwargs={"target": log_app_state}).tag("log_app_state")

    for i, region in enumerate(RegionId):
        schedule.every(1).hours.at(":{:02d}".format(i * 20)).do(
            job_func=run_threaded, kwargs={"target": get_ladders, "region_id": region.value}
        ).tag(f"get_ladders_region_id_{region.value}")

        schedule.every(20).minutes.at(":{:02d}".format(i * 1)).do(
            job_func=run_threaded, kwargs={"target": get_ladder_members, "region_id": region.value}
        ).tag(f"get_ladder_members_region_id_{region.value}")

        schedule.every(1).minutes.at(":{:02d}".format(i * 20)).do(
            job_func=run_threaded, kwargs={"target": get_ladder_results, "region_id": region.value}
        ).tag(f"get_ladder_results_region_id_{region.value}")

    # schedule.every(1).hours.do(job_func=run_threaded, kwargs={"target": create_games}).tag("create_games")

    while True:
        schedule.run_pending()
        time.sleep(1)


def handle_process(process):
    threads = []
    logger.info(f"Starting single execution of {process=}")
    if process == "ladder":
        for region in RegionId:
            threads.append(run_threaded(kwargs={"target": get_ladders, "region_id": region.value}))
    elif process == "ladder_members":
        for region in RegionId:
            threads.append(run_threaded(kwargs={"target": get_ladder_members, "region_id": region.value}))
    elif process == "ladder_results":
        for region in RegionId:
            threads.append(run_threaded(kwargs={"target": get_ladder_results, "region_id": region.value}))
    elif process == "match":
        for region in RegionId:
            threads.append(run_threaded(kwargs={"target": get_matches, "region_id": region.value}))
    # elif process == "games":
    #     threads.append(run_threaded(kwargs={"target": create_games}))
    elif process == "app_state":
        threads.append(run_threaded(kwargs={"target": log_app_state}))
    else:
        logger.error(f"Unable to execute {process=}")

    while True:
        time.sleep(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--process")
    parser.add_argument("-s", "--schedule", action="store_true")
    args = parser.parse_args()

    if args.schedule:
        handle_schedule()
    elif args.process:
        handle_process(args.process)
    else:
        logger.error("Missing required argument.")
