import os, pytz
from dotenv import load_dotenv

load_dotenv(override=True)

PLAYER_USERNAME = os.getenv("PLAYER_USERNAME")
PLAYER_PASSWORD = os.getenv("PLAYER_PASSWORD")
TIMEZONE = pytz.timezone("America/Sao_Paulo")
