import argparse
import logging

from backend.etl.character import get_characters
from backend.etl.ladder import get_ladders
from backend.etl.match import get_matches

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("-pipeline")
    args = parser.parse_args()

    if args.pipeline == "ladder":
        get_ladders()
        get_characters()
    elif args.pipeline == "match":
        get_matches()
    else:
        logging.error(f"Unsupported pipeline arg. {args.pipeline=}")
