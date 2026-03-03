import os
import pathlib
from typing import Literal
from dotenv import load_dotenv

from api2.debug import debug_kv, get_logger


ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"

# Load .env from the backend directory
load_dotenv(dotenv_path=str(ROOT / ".env"))

logger = get_logger("globals")
ENVIRONMENT = (os.getenv("ENVIRONMENT") or "development").strip().lower()

if ENVIRONMENT not in {"production", "development"}:
    raise ValueError(f"Invalid ENVIRONMENT value: {ENVIRONMENT}. Must be 'production' or 'development'.")

IS_PRODUCTION = ENVIRONMENT == "production"
logger.info("Running in %s mode", ENVIRONMENT)

if IS_PRODUCTION:
    SESSION_SECRET = os.getenv("SESSION_SECRET") or "melobytesarebestbytes"
    OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI") or "https://api.example.com/auth"
    SESSION_SAME_SITE="lax"
    SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "true").lower() == "true"
    FRONTEND_URL = os.getenv("FRONTEND_URL") or "https://fluxmod-frontend.onrender.com"
    OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "fluxer").lower()
    FLUXER_SCOPE = os.getenv("FLUXER_SCOPE", "identify guilds")
else:
    SESSION_SECRET = os.getenv("SESSION_SECRET") or "melobytesarebestbytes"
    OAUTH_REDIRECT_URI = "http://localhost:8000/auth"
    SESSION_SAME_SITE="lax"
    SESSION_HTTPS_ONLY = False
    FRONTEND_URL = "http://localhost:3000"
    OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "fluxer").lower()
    FLUXER_SCOPE = os.getenv("FLUXER_SCOPE", "identify guilds")

def build_allowed_origins() -> list[str]:
    defaults = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://fluxmod-frontend.onrender.com"
    }

    if FRONTEND_URL:
        defaults.add(FRONTEND_URL)

    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    parsed_env_origins = {
        origin.strip()
        for origin in env_origins.split(",")
        if origin.strip()
    }

    origins = sorted(defaults | parsed_env_origins)
    debug_kv(
        logger,
        "Allowed origins resolved",
        frontend_url=FRONTEND_URL,
        count=len(origins),
    )
    return origins