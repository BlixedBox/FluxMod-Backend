import os
import pathlib
from dotenv import load_dotenv

from api2.debug import debug_kv, get_logger


ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"

# Load .env from the backend directory
load_dotenv(dotenv_path=str(ROOT / ".env"))

logger = get_logger("globals")
ENVIRONMENT = (os.getenv("ENVIRONMENT") or "development").strip().lower()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_session_same_site(default_value: str) -> str:
    raw = (os.getenv("SESSION_SAME_SITE") or default_value).strip().lower()
    valid_values = {"lax", "strict", "none"}
    if raw not in valid_values:
        raise ValueError(
            f"Invalid SESSION_SAME_SITE value: {raw}. Must be one of {sorted(valid_values)}."
        )
    return "None" if raw == "none" else raw


def _resolve_session_lifetime_days(default_value: int) -> int:
    raw = os.getenv("SESSION_LIFETIME_DAYS")
    if raw is None:
        return default_value
    try:
        lifetime_days = int(raw)
    except ValueError as exc:
        raise ValueError("SESSION_LIFETIME_DAYS must be an integer") from exc

    if lifetime_days <= 0:
        raise ValueError("SESSION_LIFETIME_DAYS must be greater than 0")
    return lifetime_days

if ENVIRONMENT not in {"production", "development"}:
    raise ValueError(
        f"Invalid ENVIRONMENT value: {ENVIRONMENT}. Must be 'production' or 'development'."
    )

IS_PRODUCTION = ENVIRONMENT == "production"
logger.info("Running in %s mode", ENVIRONMENT)

if IS_PRODUCTION:
    SESSION_SECRET = os.getenv("SESSION_SECRET") or "melobytesarebestbytes"
    OAUTH_REDIRECT_URI = (
        os.getenv("OAUTH_REDIRECT_URI") or "https://api.example.com/auth"
    )
    configured_same_site = _resolve_session_same_site("none")
    SESSION_SAME_SITE = "None"
    SESSION_HTTPS_ONLY = _env_bool("SESSION_HTTPS_ONLY", True)
    SESSION_LIFETIME_DAYS = _resolve_session_lifetime_days(30)
    FRONTEND_URL = os.getenv("FRONTEND_URL") or "https://fluxmod-frontend.onrender.com"
    OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "fluxer").lower()
    FLUXER_SCOPE = os.getenv("FLUXER_SCOPE", "identify guilds")

    if configured_same_site != "None":
        logger.warning(
            "Ignoring SESSION_SAME_SITE=%s in production and forcing SameSite=None for cross-origin credentialed sessions.",
            configured_same_site,
        )

    if SESSION_SAME_SITE == "None" and not SESSION_HTTPS_ONLY:
        raise ValueError(
            "Production requires SESSION_HTTPS_ONLY=true when SESSION_SAME_SITE=none"
        )
else:
    SESSION_SECRET = os.getenv("SESSION_SECRET") or "melobytesarebestbytes"
    OAUTH_REDIRECT_URI = "http://localhost:8000/auth"
    SESSION_SAME_SITE = _resolve_session_same_site("lax")
    SESSION_HTTPS_ONLY = _env_bool("SESSION_HTTPS_ONLY", False)
    SESSION_LIFETIME_DAYS = _resolve_session_lifetime_days(7)
    FRONTEND_URL = "http://localhost:3000"
    OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "fluxer").lower()
    FLUXER_SCOPE = os.getenv("FLUXER_SCOPE", "identify guilds")


def build_allowed_origins() -> list[str]:
    defaults = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "https://fluxmod-frontend.onrender.com",
        "https://fluxmod.app",
        "https://www.fluxmod.app",
        "https://api.fluxmod.app"
    }

    if FRONTEND_URL:
        defaults.add(FRONTEND_URL)

    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    parsed_env_origins = {
        origin.strip() for origin in env_origins.split(",") if origin.strip()
    }

    origins = sorted(defaults | parsed_env_origins)
    debug_kv(
        logger,
        "Allowed origins resolved",
        frontend_url=FRONTEND_URL,
        count=len(origins),
    )
    return origins
