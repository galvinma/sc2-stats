import os

from dotenv import load_dotenv

load_dotenv()

BLIZZARD_OATH_BASE = "https://oauth.battle.net"
BLIZZARD_API_BASE = "https://{region}.api.blizzard.com"
BLIZZARD_CLIENT_ID = os.environ.get("BLIZZARD_CLIENT_ID")
BLIZZARD_CLIENT_SECRET = os.environ.get("BLIZZARD_CLIENT_SECRET")
