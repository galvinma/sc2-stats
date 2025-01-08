import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# Paths
APPLICATION_LOG_PATH = Path("/app/log/sc2_stats.log")

# API
BLIZZARD_OATH_BASE = "https://oauth.battle.net"
BLIZZARD_API_BASE = "https://{region}.api.blizzard.com"
BLIZZARD_CLIENT_ID = os.environ.get("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.environ.get("BLIZZARD_CLIENT_SECRET")

# Match
MATCH_LOOKUP_KEY = "{map}_{type}_{date}_{speed}"
MATCH_LOOKBACK_MAX = 86400  # Assume games will be reported within 24 hours
MATCH_LOOKBACK_MIN = 3600 * 7  # Maximum game time 6hours, 30mins, 6seconds. Round to 7hrs for API time buffer

# Batch
LADDER_BATCH_SIZE = 50
PROFILE_BATCH_SIZE = 500
MATCH_BATCH_SIZE = 5000

# Constraints
LEAGUE_UNIQUE_CONSTRAINT = "league_unique_constraint"
LADDER_UNIQUE_CONSTRAINT = "ladder_unique_constraint"
LADDER_MEMBER_UNIQUE_CONSTRAINT = "ladder_member_unique_constraint"
CHARACTER_MMR_UNIQUE_CONSTRAINT = "character_mmr_unique_constraint"
CHARACTER_UNIQUE_CONSTRAINT = "character_unique_constraint"
PROFILE_UNIQUE_CONSTRAINT = "profile_unique_constraint"
MATCH_UNIQUE_CONSTRAINT = "match_unique_constraint"
