from api2.database.mongo import MongoDB
from typing import List, Dict, Optional

db = MongoDB()
guilds = db.collection("guild_settings")


def get_rules(guild_id: int) -> List[Dict]:
    """Return all automod rules for a guild."""

    guild = guilds.find_one({"guild_id": guild_id}, {"automod_rules": 1, "_id": 0})

    if not guild:
        return []

    return guild.get("automod_rules", [])


def get_enabled_rules(guild_id: int) -> List[Dict]:
    """Return only enabled rules."""

    rules = get_rules(guild_id)

    return [rule for rule in rules if rule.get("enabled", False)]


def get_rule(guild_id: int, rule_name: str) -> Optional[Dict]:
    """Return a specific rule by name."""

    rules = get_rules(guild_id)

    for rule in rules:
        if rule.get("rule_name") == rule_name or rule.get("name") == rule_name:
            return rule

    return None


def add_rule(guild_id: int, rule: Dict) -> None:
    """Append one automod rule into a guild document."""

    if "keywords" not in rule:
        raw_keywords = rule.get("keyword", [])
        if isinstance(raw_keywords, str):
            rule["keywords"] = [raw_keywords.strip()] if raw_keywords.strip() else []
        elif isinstance(raw_keywords, list):
            rule["keywords"] = [
                str(item).strip() for item in raw_keywords if str(item).strip()
            ]
        else:
            rule["keywords"] = []

    if "allowed_patterns" not in rule:
        raw_allowed_patterns = rule.get("allowed_keywords", [])
        if isinstance(raw_allowed_patterns, str):
            rule["allowed_patterns"] = (
                [raw_allowed_patterns.strip()] if raw_allowed_patterns.strip() else []
            )
        elif isinstance(raw_allowed_patterns, list):
            rule["allowed_patterns"] = [
                str(item).strip()
                for item in raw_allowed_patterns
                if str(item).strip()
            ]
        else:
            rule["allowed_patterns"] = []

    guilds.update_one(
        {"guild_id": guild_id},
        {"$push": {"automod_rules": rule}},
        upsert=True,
    )


def update_rule_by_id(rule_id: str, updates: Dict) -> Optional[Dict]:
    """Update a rule by id across all guilds, returning updated rule if found."""

    result = guilds.update_one(
        {"automod_rules.id": rule_id},
        {
            "$set": {
                "automod_rules.$.name": updates.get("name"),
                "automod_rules.$.keywords": updates.get(
                    "keywords", updates.get("keyword", [])
                ),
                "automod_rules.$.allowed_patterns": updates.get(
                    "allowed_patterns", updates.get("allowed_keywords", [])
                ),
                "automod_rules.$.allowed_keywords": updates.get(
                    "allowed_patterns", updates.get("allowed_keywords", [])
                ),
                "automod_rules.$.pattern": updates.get("pattern"),
                "automod_rules.$.action": updates.get("action"),
                "automod_rules.$.severity": updates.get("severity", 2),
                "automod_rules.$.threshold": updates.get("threshold"),
                "automod_rules.$.enabled": updates.get("enabled"),
                "automod_rules.$.exempt_role_ids": updates.get("exempt_role_ids", []),
                "automod_rules.$.exempt_roles": updates.get("exempt_role_ids", []),
                "automod_rules.$.exempt_channel_ids": updates.get(
                    "exempt_channel_ids", []
                ),
                "automod_rules.$.exempt_channels": updates.get(
                    "exempt_channel_ids", []
                ),
                "automod_rules.$.exempt_user_ids": updates.get("exempt_user_ids", []),
                "automod_rules.$.exempt_users": updates.get("exempt_user_ids", []),
                "automod_rules.$.escalation_enabled": updates.get(
                    "escalation_enabled", False
                ),
                "automod_rules.$.escalation_warn_threshold": updates.get(
                    "escalation_warn_threshold", 1
                ),
                "automod_rules.$.escalation_action": updates.get(
                    "escalation_action", "timeout"
                ),
                "automod_rules.$.escalation_timeout_duration": updates.get(
                    "escalation_timeout_duration", 10
                ),
                "automod_rules.$.escalation_reset_minutes": updates.get(
                    "escalation_reset_minutes", 0
                ),
                "automod_rules.$.offense_escalation_enabled": updates.get(
                    "escalation_enabled", False
                ),
                "automod_rules.$.offense_escalation_action": updates.get(
                    "escalation_action", "timeout"
                ),
                "automod_rules.$.escalation": updates.get(
                    "escalation",
                    {
                        "enabled": updates.get("escalation_enabled", False),
                        "warn_threshold": updates.get(
                            "escalation_warn_threshold", 1
                        ),
                        "action": updates.get("escalation_action", "timeout"),
                        "timeout_duration": updates.get(
                            "escalation_timeout_duration", 10
                        ),
                        "reset_minutes": updates.get("escalation_reset_minutes", 0),
                    },
                ),
            }
        },
    )

    if result.matched_count == 0:
        return None

    guild = guilds.find_one(
        {"automod_rules.id": rule_id},
        {"automod_rules": 1, "guild_id": 1, "_id": 0},
    )

    if not guild:
        return None

    for rule in guild.get("automod_rules", []):
        if rule.get("id") == rule_id:
            return {"guild_id": str(guild.get("guild_id")), **rule}

    return None


def delete_rule_by_id(rule_id: str) -> bool:
    """Delete a rule by id across all guilds."""

    result = guilds.update_one(
        {"automod_rules.id": rule_id},
        {"$pull": {"automod_rules": {"id": rule_id}}},
    )

    return result.modified_count > 0


def get_guild_id_by_rule_id(rule_id: str) -> int | None:
    """Return guild_id that owns a rule id, if present."""

    guild = guilds.find_one({"automod_rules.id": rule_id}, {"guild_id": 1, "_id": 0})
    if not guild:
        return None

    guild_id = guild.get("guild_id")
    return guild_id if isinstance(guild_id, int) else None
