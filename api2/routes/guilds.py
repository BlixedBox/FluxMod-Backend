from __future__ import annotations

from flask import Blueprint, jsonify, request

from api2.database.guilds import (
    create_guild,
    get_command_settings,
    get_guild,
    update_command_settings,
    get_lhs_settings,
    update_lhs_settings,
    set_lhs_enabled,
)
from api2.debug import debug_kv, get_logger
from api2.services.auth_helpers import require_user
from api2.services.validators import ValidationError, parse_rule_payload
from api2.utils.datawrapper import DataWrapper


guilds_bp = Blueprint("guilds", __name__)
logger = get_logger("routes.guilds")
data_wrapper = DataWrapper()


def _parse_guild_id_query_param() -> tuple[
    str | None, int | None, tuple[dict, int] | None
]:
    guild_id = (request.args.get("guild_id") or "").strip()
    if not guild_id:
        return None, None, ({"detail": "guild_id query parameter is required"}, 400)
    if not guild_id.isdigit():
        return None, None, ({"detail": "guild_id must be a numeric string"}, 400)

    return guild_id, int(guild_id), None


def _ensure_guild_exists(guild_id: int) -> None:
    if not get_guild(guild_id):
        create_guild(guild_id)


@guilds_bp.get("/api/guilds")
@require_user
def list_guilds():
    """List known guilds with a computed rule count per guild."""
    guilds = data_wrapper.list_guilds()

    debug_kv(logger, "Guild list generated", guild_count=len(guilds))

    return jsonify(guilds)


@guilds_bp.route("/api/guilds/settings", methods=["GET", "PUT"])
@require_user
def guild_settings_by_query_param():
    """Compatibility endpoint for guild command settings via query string."""
    guild_id_str, guild_id, error = _parse_guild_id_query_param()
    if error is not None:
        payload, status_code = error
        return jsonify(payload), status_code

    assert guild_id is not None and guild_id_str is not None

    if request.method == "GET":
        settings = get_command_settings(guild_id)
        debug_kv(
            logger,
            "Guild command settings fetched",
            guild_id=guild_id_str,
            field_count=len(settings) if isinstance(settings, dict) else 0,
        )
        return jsonify(settings if isinstance(settings, dict) else {})

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"detail": "JSON body must be an object"}), 400

    _ensure_guild_exists(guild_id)
    update_command_settings(guild_id, payload)
    debug_kv(
        logger,
        "Guild command settings updated",
        guild_id=guild_id_str,
        field_count=len(payload),
    )
    return jsonify(payload)


@guilds_bp.route("/api/guilds/settings/automod", methods=["GET", "PUT"])
@require_user
def automod_settings_by_query_param():
    """Compatibility endpoint for automod settings nested in command settings."""
    guild_id_str, guild_id, error = _parse_guild_id_query_param()
    if error is not None:
        payload, status_code = error
        return jsonify(payload), status_code

    assert guild_id is not None and guild_id_str is not None

    settings = get_command_settings(guild_id)
    if not isinstance(settings, dict):
        settings = {}

    if request.method == "GET":
        automod_settings = settings.get("automod_settings")
        if not isinstance(automod_settings, dict):
            automod_settings = settings.get("automod")
        if not isinstance(automod_settings, dict):
            automod_settings = {}

        debug_kv(
            logger,
            "Guild automod settings fetched",
            guild_id=guild_id_str,
            field_count=len(automod_settings),
        )
        return jsonify(automod_settings)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"detail": "JSON body must be an object"}), 400

    _ensure_guild_exists(guild_id)
    settings["automod_settings"] = payload
    update_command_settings(guild_id, settings)
    debug_kv(
        logger,
        "Guild automod settings updated",
        guild_id=guild_id_str,
        field_count=len(payload),
    )
    return jsonify(payload)


@guilds_bp.route("/api/guilds/automod-settings", methods=["GET", "PUT"])
@require_user
def automod_settings_legacy_path():
    """Legacy path alias for automod settings compatibility."""
    return automod_settings_by_query_param()


@guilds_bp.get("/api/guilds/<guild_id>/rules")
@require_user
def list_rules(guild_id: str):
    """Return all rules for one guild."""
    rules = data_wrapper.list_rules_for_guild(guild_id)
    debug_kv(logger, "Rules listed for guild", guild_id=guild_id, rule_count=len(rules))
    return jsonify(rules)


@guilds_bp.get("/api/guilds/rules")
@require_user
def list_rules_by_query_param():
    """Compatibility endpoint for clients that pass guild_id as query string."""
    guild_id = (request.args.get("guild_id") or "").strip()
    if not guild_id:
        return jsonify({"detail": "guild_id query parameter is required"}), 400

    rules = data_wrapper.list_rules_for_guild(guild_id)
    debug_kv(
        logger,
        "Rules listed for guild via query param",
        guild_id=guild_id,
        rule_count=len(rules),
    )
    return jsonify(rules)


@guilds_bp.post("/api/guilds/<guild_id>/rules")
@require_user
def create_rule(guild_id: str):
    """Create a new rule inside the selected guild."""
    if not guild_id.isdigit():
        return jsonify({"detail": "guild_id must be a numeric string"}), 400

    payload = request.get_json(silent=True) or {}
    debug_kv(
        logger,
        "Create rule payload received",
        guild_id=guild_id,
        fields=list(payload.keys()),
    )

    try:
        normalized = parse_rule_payload(payload)
    except ValidationError as exc:
        debug_kv(
            logger,
            "Create rule payload validation failed",
            guild_id=guild_id,
            error=str(exc),
        )
        return jsonify({"detail": str(exc)}), 400

    rule = data_wrapper.create_rule(guild_id, normalized)
    debug_kv(logger, "Rule created", guild_id=guild_id, rule_id=rule.get("id"))

    return jsonify(rule), 201


@guilds_bp.post("/api/guilds/rules")
@require_user
def create_rule_by_query_param():
    """Compatibility endpoint for creating a rule with guild_id in query string."""
    guild_id = (request.args.get("guild_id") or "").strip()
    if not guild_id:
        return jsonify({"detail": "guild_id query parameter is required"}), 400
    if not guild_id.isdigit():
        return jsonify({"detail": "guild_id must be a numeric string"}), 400

    payload = request.get_json(silent=True) or {}
    debug_kv(
        logger,
        "Create rule payload received via query param",
        guild_id=guild_id,
        fields=list(payload.keys()),
    )

    try:
        normalized = parse_rule_payload(payload)
    except ValidationError as exc:
        debug_kv(
            logger,
            "Create rule payload validation failed via query param",
            guild_id=guild_id,
            error=str(exc),
        )
        return jsonify({"detail": str(exc)}), 400

    rule = data_wrapper.create_rule(guild_id, normalized)
    debug_kv(
        logger,
        "Rule created via query param",
        guild_id=guild_id,
        rule_id=rule.get("id"),
    )

    return jsonify(rule), 201


@guilds_bp.put("/api/rules/<rule_id>")
@require_user
def update_rule(rule_id: str):
    """Update an existing rule by id."""
    payload = request.get_json(silent=True) or {}
    debug_kv(
        logger,
        "Update rule payload received",
        rule_id=rule_id,
        fields=list(payload.keys()),
    )

    try:
        normalized = parse_rule_payload(payload)
    except ValidationError as exc:
        debug_kv(
            logger,
            "Update rule payload validation failed",
            rule_id=rule_id,
            error=str(exc),
        )
        return jsonify({"detail": str(exc)}), 400

    updated_rule = data_wrapper.update_rule(rule_id, normalized)
    if updated_rule is not None:
        debug_kv(logger, "Rule updated", rule_id=rule_id)
        return jsonify(updated_rule)

    debug_kv(logger, "Rule update target not found", rule_id=rule_id)
    return jsonify({"detail": "rule not found"}), 404


@guilds_bp.put("/api/guilds/rules/<rule_id>")
@require_user
def update_rule_by_query_param(rule_id: str):
    """Compatibility endpoint for updating a rule by id via guilds-prefixed path."""
    payload = request.get_json(silent=True) or {}
    guild_id = (request.args.get("guild_id") or "").strip()
    debug_kv(
        logger,
        "Update rule payload received via query-param path",
        rule_id=rule_id,
        guild_id=guild_id or None,
        fields=list(payload.keys()),
    )

    try:
        normalized = parse_rule_payload(payload)
    except ValidationError as exc:
        debug_kv(
            logger,
            "Update rule payload validation failed via query-param path",
            rule_id=rule_id,
            guild_id=guild_id or None,
            error=str(exc),
        )
        return jsonify({"detail": str(exc)}), 400

    updated_rule = data_wrapper.update_rule(rule_id, normalized)
    if updated_rule is not None:
        debug_kv(
            logger,
            "Rule updated via query-param path",
            rule_id=rule_id,
            guild_id=guild_id or None,
        )
        return jsonify(updated_rule)

    debug_kv(
        logger,
        "Rule update target not found via query-param path",
        rule_id=rule_id,
        guild_id=guild_id or None,
    )
    return jsonify({"detail": "rule not found"}), 404


@guilds_bp.delete("/api/rules/<rule_id>")
@require_user
def delete_rule(rule_id: str):
    """Delete a rule by id."""
    if data_wrapper.delete_rule(rule_id):
        debug_kv(logger, "Rule deleted", rule_id=rule_id)
        return "", 204

    debug_kv(logger, "Rule delete target not found", rule_id=rule_id)
    return jsonify({"detail": "rule not found"}), 404


@guilds_bp.delete("/api/guilds/rules/<rule_id>")
@require_user
def delete_rule_by_query_param(rule_id: str):
    """Compatibility endpoint for deleting a rule by id via guilds-prefixed path."""
    guild_id = (request.args.get("guild_id") or "").strip()

    if data_wrapper.delete_rule(rule_id):
        debug_kv(
            logger,
            "Rule deleted via query-param path",
            rule_id=rule_id,
            guild_id=guild_id or None,
        )
        return "", 204

    debug_kv(
        logger,
        "Rule delete target not found via query-param path",
        rule_id=rule_id,
        guild_id=guild_id or None,
    )
    return jsonify({"detail": "rule not found"}), 404


# LHS (AI Moderation) endpoints


@guilds_bp.route("/api/guilds/lhs-settings", methods=["GET", "PUT"])
@require_user
def lhs_settings_by_query_param():
    """Endpoint for LHS (AI Moderation) settings."""
    guild_id_str, guild_id, error = _parse_guild_id_query_param()
    if error is not None:
        payload, status_code = error
        return jsonify(payload), status_code

    assert guild_id is not None and guild_id_str is not None

    if request.method == "GET":
        settings = get_lhs_settings(guild_id)
        debug_kv(
            logger,
            "LHS settings fetched",
            guild_id=guild_id_str,
        )
        return jsonify(settings)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"detail": "JSON body must be an object"}), 400

    _ensure_guild_exists(guild_id)
    update_lhs_settings(guild_id, payload)
    debug_kv(
        logger,
        "LHS settings updated",
        guild_id=guild_id_str,
        fields=list(payload.keys()),
    )
    return jsonify(payload)


@guilds_bp.route("/api/guilds/lhs-enabled", methods=["GET", "PUT"])
@require_user
def lhs_enabled_endpoint():
    """Enable/disable LHS for a guild."""
    guild_id_str, guild_id, error = _parse_guild_id_query_param()
    if error is not None:
        payload, status_code = error
        return jsonify(payload), status_code

    assert guild_id is not None and guild_id_str is not None

    if request.method == "GET":
        settings = get_lhs_settings(guild_id)
        return jsonify({"enabled": settings.get("enabled", False)})

    payload = request.get_json(silent=True) or {}
    enabled = payload.get("enabled")
    
    if enabled is None:
        return jsonify({"detail": "enabled field is required"}), 400

    _ensure_guild_exists(guild_id)
    set_lhs_enabled(guild_id, bool(enabled))
    debug_kv(
        logger,
        "LHS enabled state updated",
        guild_id=guild_id_str,
        enabled=bool(enabled),
    )
    return jsonify({"enabled": bool(enabled)})
