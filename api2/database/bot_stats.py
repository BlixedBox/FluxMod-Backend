from api2.database.mongo import MongoDB


db = MongoDB()
bot_stats = db.collection("bot_stats")


def get_global_guild_count() -> int:
    """Return guild count from the global bot_stats document."""

    document = bot_stats.find_one({"_id": "global"}, {"guild_count": 1, "_id": 0})
    if not document:
        return 0

    guild_count = document.get("guild_count")
    return guild_count if isinstance(guild_count, int) else 0
