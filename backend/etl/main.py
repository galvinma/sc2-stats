import argparse
import time

import schedule
from dotenv import load_dotenv

from backend.etl.game import create_games
from backend.etl.ladder import get_ladders
from backend.etl.ladder_member import get_ladder_members
from backend.etl.ladder_result import get_ladder_results
from backend.utils.logging_utils import get_logger

load_dotenv()

logger = get_logger(__name__)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--process")
    parser.add_argument("-s", "--schedule", action="store_true")
    args = parser.parse_args()

    if args.process == "ladder":
        get_ladders()
    if args.process == "ladder_members":
        get_ladder_members()
    elif args.process == "ladder_results":
        get_ladder_results()
    elif args.process == "games":
        create_games()
    elif args.process == "all":
        get_ladders()
        get_ladder_members()
        get_ladder_results()
        create_games()

    if args.schedule:
        schedule.every(30).seconds.do(get_ladder_results)
        schedule.every(5).minutes.do(get_ladders)
        schedule.every(5).minutes.do(get_ladder_members)
        schedule.every(5).minutes.do(create_games)

        while True:
            schedule.run_pending()
            time.sleep(1)
