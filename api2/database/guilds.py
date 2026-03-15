from api2.database.mongo import MongoDB
from typing import Dict, Any

db = MongoDB()
guilds = db.collection("guild_settings")


# LHS Settings defaults
DEFAULT_LHS_SETTINGS = {
    "enabled": False,
    "global_threshold": 0.55,
    "categories": {},
    "exempt_roles": [],
    "exempt_channels": [],
    "exempt_users": [],
    "action": "delete",
    "severity": 2,
    "log_only_mode": False,
    "channel_overrides": {},
}


def create_guild(guild_id: int):

    if guilds.find_one({"guild_id": guild_id}):
        return

    guilds.insert_one(
        {"guild_id": guild_id, "automod_rules": [], "command_settings": {}, "warns": []}
    )


def get_guild(guild_id: int):
    return guilds.find_one({"guild_id": guild_id})


def get_all_guilds() -> list[dict]:
    return list(guilds.find({}, {"_id": 0}))


def get_command_settings(guild_id: int) -> dict:

    guild = guilds.find_one({"guild_id": guild_id}, {"command_settings": 1, "_id": 0})

    if not guild:
        return {}

    return guild.get("command_settings", {})


def update_command_settings(guild_id: int, settings: dict):

    guilds.update_one({"guild_id": guild_id}, {"$set": {"command_settings": settings}})


def set_log_channel_id(guild_id: int, channel_id: int):

    guilds.update_one(
        {"guild_id": guild_id},
        {"$set": {"command_settings.log_channel_id": channel_id}},
        upsert=True,
    )


def get_log_channel_id(guild_id: int) -> int | None:

    guild = guilds.find_one(
        {"guild_id": guild_id}, {"command_settings.log_channel_id": 1, "_id": 0}
    )

    if not guild:
        return None

    command_settings = guild.get("command_settings", {})
    channel_id = command_settings.get("log_channel_id")

    return channel_id if isinstance(channel_id, int) else None


def get_lhs_settings(guild_id: int) -> Dict[str, Any]:
    """
    Get LHS (AI Moderation) settings for a guild.
    Returns default settings if none exist.
    """
    guild = guilds.find_one(
        {"guild_id": guild_id},
        {"lhs_settings": 1, "_id": 0}
    )
    
    if not guild:
        return DEFAULT_LHS_SETTINGS.copy()
    
    stored_settings = guild.get("lhs_settings", {})
    
    # Merge with defaults
    settings = DEFAULT_LHS_SETTINGS.copy()
    settings.update(stored_settings)
    
    return settings


def update_lhs_settings(guild_id: int, settings: Dict[str, Any]) -> None:
    """
    Update LHS settings for a guild.
    """
    guilds.update_one(
        {"guild_id": guild_id},
        {
            "$set": {"lhs_settings": settings},
            "$setOnInsert": {
                "guild_id": guild_id,
                "automod_rules": [],
                "warns": [],
                "command_settings": {},
            },
        },
        upsert=True,
    )


def set_lhs_enabled(guild_id: int, enabled: bool) -> None:
    """Enable or disable LHS for a guild."""
    guilds.update_one(
        {"guild_id": guild_id},
        {
            "$set": {"lhs_settings.enabled": bool(enabled)},
            "$setOnInsert": {
                "guild_id": guild_id,
                "automod_rules": [],
                "warns": [],
                "command_settings": {},
            },
        },
        upsert=True,
    )
