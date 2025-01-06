import os

from dotenv import load_dotenv

load_dotenv()

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
