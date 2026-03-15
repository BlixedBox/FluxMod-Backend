from __future__ import annotations

from api2.debug import debug_kv, get_logger


class ValidationError(ValueError):
    """Raised when request data fails backend validation."""


REQUIRED_RULE_FIELDS = {"name", "action"}
logger = get_logger("services.validators")


def _pick_first_defined(source: dict, *keys: str) -> object:
    for key in keys:
        if key in source and source.get(key) is not None:
            return source.get(key)

    return None


def _parse_positive_int(value: object, field_name: str, *, min_value: int = 1, max_value: int | None = None) -> int:
    parsed: int | None = None

    if isinstance(value, bool):
        parsed = None
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and value.is_integer():
        parsed = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("+-").isdigit():
            parsed = int(text)

    if parsed is None:
        debug_kv(logger, "Invalid integer-like field received", field=field_name, value=value)
        if max_value is None:
            raise ValidationError(f"{field_name} must be an integer >= {min_value}")
        raise ValidationError(f"{field_name} must be an integer between {min_value} and {max_value}")

    if parsed < min_value or (max_value is not None and parsed > max_value):
        debug_kv(logger, "Out-of-range integer field received", field=field_name, value=parsed)
        if max_value is None:
            raise ValidationError(f"{field_name} must be an integer >= {min_value}")
        raise ValidationError(f"{field_name} must be an integer between {min_value} and {max_value}")

    return parsed


def _parse_bool_like(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False

    debug_kv(logger, "Invalid boolean-like field received", field=field_name, value=value)
    raise ValidationError(f"{field_name} must be a boolean")


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

    threshold = _parse_positive_int(payload.get("threshold", 1), "threshold", min_value=1)

    severity = _parse_positive_int(payload.get("severity", 2), "severity", min_value=1, max_value=5)

    enabled = _parse_bool_like(payload.get("enabled", True), "enabled")

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

    pattern_value = payload.get("pattern", "")
    if pattern_value is None:
        pattern = ""
    elif isinstance(pattern_value, str):
        pattern = pattern_value.strip()
    else:
        debug_kv(logger, "Invalid pattern type received", pattern=pattern_value)
        raise ValidationError("pattern must be a string")

    if not keywords and not pattern:
        raise ValidationError("A rule must include at least one keyword or one regex pattern")

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
    allowed_patterns = _parse_optional_string_list(
        payload,
        "allowed_patterns",
        "allowed_keywords",
        "allowedPatterns",
        "allowedKeywords",
    )

    escalation_payload = payload.get("escalation")
    if not isinstance(escalation_payload, dict):
        escalation_payload = {}

    escalation_enabled_raw = _pick_first_defined(
        payload,
        "escalation_enabled",
        "escalationEnabled",
        "offense_escalation_enabled",
        "offenseEscalationEnabled",
    )
    if escalation_enabled_raw is None:
        escalation_enabled_raw = _pick_first_defined(
            escalation_payload,
            "enabled",
            "is_enabled",
            "isEnabled",
        )
    escalation_enabled = (
        _parse_bool_like(escalation_enabled_raw, "escalation_enabled")
        if escalation_enabled_raw is not None
        else False
    )

    escalation_warn_threshold_raw = _pick_first_defined(
        payload,
        "escalation_warn_threshold",
        "escalationWarnThreshold",
        "offense_escalation_warn_threshold",
        "offenseEscalationWarnThreshold",
        "warn_threshold",
        "warnThreshold",
    )
    if escalation_warn_threshold_raw is None:
        escalation_warn_threshold_raw = _pick_first_defined(
            escalation_payload,
            "warn_threshold",
            "warnThreshold",
        )
    escalation_warn_threshold = _parse_positive_int(
        escalation_warn_threshold_raw if escalation_warn_threshold_raw is not None else 1,
        "escalation_warn_threshold",
        min_value=1,
    )

    escalation_action_raw = _pick_first_defined(
        payload,
        "escalation_action",
        "escalationAction",
        "offense_escalation_action",
        "offenseEscalationAction",
    )
    if escalation_action_raw is None:
        escalation_action_raw = _pick_first_defined(escalation_payload, "action")
    escalation_action = str(escalation_action_raw if escalation_action_raw is not None else "timeout").strip()
    if not escalation_action:
        escalation_action = "timeout"

    escalation_timeout_duration_raw = _pick_first_defined(
        payload,
        "escalation_timeout_duration",
        "escalationTimeoutDuration",
        "offense_escalation_timeout_duration",
        "offenseEscalationTimeoutDuration",
    )
    if escalation_timeout_duration_raw is None:
        escalation_timeout_duration_raw = _pick_first_defined(
            escalation_payload,
            "timeout_duration",
            "timeoutDuration",
        )
    escalation_timeout_duration = _parse_positive_int(
        escalation_timeout_duration_raw if escalation_timeout_duration_raw is not None else 10,
        "escalation_timeout_duration",
        min_value=1,
    )

    escalation_reset_minutes_raw = _pick_first_defined(
        payload,
        "escalation_reset_minutes",
        "escalationResetMinutes",
        "offense_escalation_reset_minutes",
        "offenseEscalationResetMinutes",
        "reset_minutes",
        "resetMinutes",
    )
    if escalation_reset_minutes_raw is None:
        escalation_reset_minutes_raw = _pick_first_defined(
            escalation_payload,
            "reset_minutes",
            "resetMinutes",
        )
    escalation_reset_minutes = _parse_positive_int(
        escalation_reset_minutes_raw if escalation_reset_minutes_raw is not None else 0,
        "escalation_reset_minutes",
        min_value=0,
    )

    return {
        "name": str(payload["name"]),
        "pattern": pattern,
        "action": str(payload["action"]),
        "severity": severity,
        "keywords": keywords,
        "allowed_patterns": allowed_patterns,
        "threshold": threshold,
        "enabled": enabled,
        "exempt_role_ids": exempt_role_ids,
        "exempt_channel_ids": exempt_channel_ids,
        "exempt_user_ids": exempt_user_ids,
        "escalation_enabled": escalation_enabled,
        "escalation_warn_threshold": escalation_warn_threshold,
        "escalation_action": escalation_action,
        "escalation_timeout_duration": escalation_timeout_duration,
        "escalation_reset_minutes": escalation_reset_minutes,
        "offense_escalation_enabled": escalation_enabled,
        "offense_escalation_action": escalation_action,
        "escalation": {
            "enabled": escalation_enabled,
            "warn_threshold": escalation_warn_threshold,
            "action": escalation_action,
            "timeout_duration": escalation_timeout_duration,
            "reset_minutes": escalation_reset_minutes,
        },
    }
