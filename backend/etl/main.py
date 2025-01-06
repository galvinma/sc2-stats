import argparse
import logging

from dotenv import load_dotenv

from backend.etl.game import create_games
from backend.etl.ladder import get_ladders
from backend.etl.ladder_member import get_ladder_members
from backend.etl.ladder_result import get_ladder_results

if __name__ == "__main__":

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("-pipeline")  # TODO Better keyword for processing ETLs
    args = parser.parse_args()

    # TODO STAT-12 Create cron/scheduling process for ETLs
    if args.pipeline == "ladder":
        get_ladders()
        get_ladder_members()
    elif args.pipeline == "ladder_results":
        get_ladder_results()
    elif args.pipeline == "game":
        create_games()

    else:
        logging.error(f"Unsupported pipeline arg. {args.pipeline=}")
