from __future__ import annotations

from api2.debug import debug_kv, get_logger


class ValidationError(ValueError):
    """Raised when request data fails backend validation."""


REQUIRED_RULE_FIELDS = {"name", "pattern", "action"}
logger = get_logger("services.validators")


def _parse_optional_string_list(payload: dict, *keys: str) -> list[str]:
    for key in keys:
        if key not in payload:
            continue

        raw_value = payload.get(key)
        if raw_value is None:
            return []

        if isinstance(raw_value, str):
            return [raw_value.strip()] if raw_value.strip() else []

        if isinstance(raw_value, list):
            if not all(isinstance(item, str) for item in raw_value):
                debug_kv(logger, "Invalid list field received", field=key, value=raw_value)
                raise ValidationError(f"{key} must be a list of strings")
            return [item.strip() for item in raw_value if item.strip()]

        debug_kv(logger, "Invalid list field type received", field=key, value=raw_value)
        raise ValidationError(f"{key} must be a list of strings")

    return []


def parse_rule_payload(payload: dict) -> dict:
    """Validate and normalize a rule payload from JSON body."""
    debug_kv(logger, "Parsing rule payload", fields=list(payload.keys()))
    missing_fields = [field for field in REQUIRED_RULE_FIELDS if field not in payload]
    if missing_fields:
        debug_kv(logger, "Missing required rule fields", missing_fields=missing_fields)
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    threshold = payload.get("threshold", 1)
    if not isinstance(threshold, int) or threshold < 1:
        debug_kv(logger, "Invalid threshold received", threshold=threshold)
        raise ValidationError("threshold must be an integer >= 1")

    enabled = payload.get("enabled", True)
    if not isinstance(enabled, bool):
        debug_kv(logger, "Invalid enabled value received", enabled=enabled)
        raise ValidationError("enabled must be a boolean")

    keywords_value = payload.get("keywords", payload.get("keyword", []))
    if isinstance(keywords_value, str):
        keywords = [keywords_value.strip()] if keywords_value.strip() else []
    elif isinstance(keywords_value, list):
        if not all(isinstance(item, str) for item in keywords_value):
            debug_kv(logger, "Invalid keywords received", keywords=keywords_value)
            raise ValidationError("keywords must be a list of strings")
        keywords = [item.strip() for item in keywords_value if item.strip()]
    elif keywords_value is None:
        keywords = []
    else:
        debug_kv(logger, "Invalid keywords type received", keywords=keywords_value)
        raise ValidationError("keywords must be a list of strings")

    exempt_role_ids = _parse_optional_string_list(
        payload,
        "exempt_role_ids",
        "exempt_roles",
        "exemptRoleIds",
        "ignored_role_ids",
    )
    exempt_channel_ids = _parse_optional_string_list(
        payload,
        "exempt_channel_ids",
        "exempt_channels",
        "exemptChannelIds",
        "ignored_channel_ids",
    )
    exempt_user_ids = _parse_optional_string_list(
        payload,
        "exempt_user_ids",
        "exempt_users",
        "exemptUserIds",
        "ignored_user_ids",
    )

    return {
        "name": str(payload["name"]),
        "pattern": str(payload["pattern"]),
        "action": str(payload["action"]),
        "keywords": keywords,
        "threshold": threshold,
        "enabled": enabled,
        "exempt_role_ids": exempt_role_ids,
        "exempt_channel_ids": exempt_channel_ids,
        "exempt_user_ids": exempt_user_ids,
    }
