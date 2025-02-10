import os

from dotenv import load_dotenv

from backend.utils.log import get_logger

load_dotenv()


logger = get_logger(__name__)


def pytest_configure(config):
    """
    https://docs.pytest.org/en/latest/reference/reference.html#pytest.hookspec.pytest_configure

    Allow plugins and conftest files to perform initial configuration.

    Use this to verify test env
    """
    SC2_STATS_DB_PATH = os.environ.get("SC2_STATS_DB_PATH")
    SC2_STATS_PG_DB = os.environ.get("SC2_STATS_PG_DB")

    if not SC2_STATS_PG_DB == "postgres" and "test/postgres" in SC2_STATS_DB_PATH:
        logger.error(f"{SC2_STATS_DB_PATH=}")
        logger.error(f"{SC2_STATS_PG_DB=}")
        raise Exception("Misconfigured env.")
