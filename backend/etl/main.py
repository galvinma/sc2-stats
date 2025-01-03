import logging
import argparse

from backend.etl.ladder import get_ladders


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser()
    parser.add_argument("-pipeline")
    args = parser.parse_args()

    if args.pipeline == "ladders":
        get_ladders()
