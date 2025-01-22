import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# Paths
APPLICATION_LOG_PATH = Path("/app/log/sc2_stats.log")

# Blizzard API
BLIZZARD_OATH_BASE = "https://oauth.battle.net"
BLIZZARD_API_BASE = "https://{region}.api.blizzard.com"
BLIZZARD_CLIENT_ID = os.environ.get("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.environ.get("BLIZZARD_CLIENT_SECRET")
REQUEST_MAX_PER_SECOND = int(100 * 0.95)  # Blizzard max 100
REQUEST_MAX_PER_DAY = int(36000 * 0.95)  # Blizzard max 36,000
BLIZZARD_503_RETRY_MAX = 3


# SC2 STATS API
SC2_STATS_API_BASE = os.environ.get("SC2_STATS_API_BASE")

# Match
MATCH_LOOKUP_KEY = "{map}_{type}_{date}_{speed}"
MATCH_LOOKBACK_MAX = 86400  # Assume games will be reported within 24 hours
MATCH_LOOKBACK_MIN = 3600 * 7  # Maximum game time 6hours, 30mins, 6seconds. Round to 7hrs for API time buffer

# Batch
LADDER_BATCH_SIZE = 50
PROFILE_BATCH_SIZE = 500
MATCH_BATCH_SIZE = 5000

# Constraints
BLIZZARD_REQUEST_UNIQUE_CONSTRAINT = "blizzard_request_pkey"
LEAGUE_UNIQUE_CONSTRAINT = "league_unique_constraint"
LADDER_UNIQUE_CONSTRAINT = "ladder_unique_constraint"
LADDER_MEMBER_UNIQUE_CONSTRAINT = "ladder_member_unique_constraint"
CHARACTER_MMR_UNIQUE_CONSTRAINT = "character_mmr_unique_constraint"
CHARACTER_UNIQUE_CONSTRAINT = "character_unique_constraint"
PROFILE_UNIQUE_CONSTRAINT = "profile_unique_constraint"
GAME_UNIQUE_CONSTRAINT = "game_pkey"
MATCH_UNIQUE_CONSTRAINT = "match_pkey"
ETL_EXECUTION_UNIQUE_CONSTRAINT = "etl_execution_pkey"


# Jobs
LADDER_JOB_NAME = "ladder"
LADDER_MEMBERS_JOB_NAME = "ladder_members"
LADDER_RESULTS_JOB_NAME = "ladder_results"
JOB_NAMES = [LADDER_JOB_NAME, LADDER_MEMBERS_JOB_NAME, LADDER_RESULTS_JOB_NAME]


# Lookup Keys
LADDER_CHARACTER_MMR_LOOKUP_KEY = "{profile_id}_{realm_id}_{region_id}_{display_name}_{race}"


# Misc.
MMR_MAX = 20000
MMR_MIN = 0
