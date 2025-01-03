import argparse
import logging

from backend.etl.ladder import get_ladder_members, get_ladders

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("-pipeline")
    args = parser.parse_args()

    if args.pipeline == "ladders":
        get_ladders()
        get_ladder_members()
