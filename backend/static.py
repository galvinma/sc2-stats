import os

from dotenv import load_dotenv

load_dotenv()

# API
BLIZZARD_OATH_BASE = "https://oauth.battle.net"
BLIZZARD_API_BASE = "https://{region}.api.blizzard.com"
BLIZZARD_CLIENT_ID = os.environ.get("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.environ.get("BLIZZARD_CLIENT_SECRET")

# Batch
LADDER_BATCH_SIZE = 50
PROFILE_BATCH_SIZE = 500
MATCH_BATCH_SIZE = 5000
