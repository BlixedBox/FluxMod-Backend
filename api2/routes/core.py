from flask import Blueprint, jsonify

from api2.debug import debug_kv, get_logger
from api2.database.bot_stats import get_global_guild_count


core_bp = Blueprint("core", __name__)
logger = get_logger("routes.core")


@core_bp.get("/")
def home():
    """Simple root endpoint to verify the API is online."""
    debug_kv(logger, "Root endpoint called")
    return jsonify({"message": "AutoMod API 2.0 (Flask)"})


@core_bp.route("/healthz", methods=["GET", "HEAD"])
def healthz():
    """Health check endpoint for uptime monitors."""
    debug_kv(logger, "Health check endpoint called")
    uptime_percent = 100.0
    return jsonify(
        {
            "status": "ok",
            "uptime24h": uptime_percent,
            "uptime_24h": uptime_percent,
            "uptimePercent": uptime_percent,
            "uptime_percent": uptime_percent,
        }
    )


@core_bp.get("/api/guild-count")
def guild_count():
    """Return the bot's global guild count."""
    count = get_global_guild_count()
    debug_kv(logger, "Guild count endpoint called", guild_count=count)
    return jsonify({"guild_count": count})
