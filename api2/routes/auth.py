from __future__ import annotations

import os
import httpx
from flask import Blueprint, jsonify, redirect, request, session

from api2.extensions import oauth
from api2.services.auth_helpers import require_user
from api2.globals import (
    FRONTEND_URL,
    FLUXER_SCOPE,
    IS_PRODUCTION,
    OAUTH_PROVIDER,
    OAUTH_REDIRECT_URI,
)

auth_bp = Blueprint("auth", __name__)


def _build_profile_endpoints() -> list[str]:
    configured = os.getenv("FLUXER_USER_ENDPOINT")
    candidates = [
        configured,
        "https://api.fluxer.app/v1/oauth2/userinfo",
        "https://api.fluxer.app/v1/users/@me",
    ]

    endpoints: list[str] = []
    for endpoint in candidates:
        if endpoint and endpoint not in endpoints:
            endpoints.append(endpoint)
    return endpoints


@auth_bp.get("/login")
def login():
    """
    Redirect user to Fluxer's OAuth2 authorize URL.
    """
    print(f"[DEBUG] Login endpoint invoked, provider={OAUTH_PROVIDER}")

    client = oauth.create_client(OAUTH_PROVIDER)
    if client is None:
        print(f"[ERROR] OAuth client not configured for provider {OAUTH_PROVIDER}")
        return jsonify({"detail": f"OAuth provider '{OAUTH_PROVIDER}' not configured"}), 500

    return client.authorize_redirect(
        redirect_uri=OAUTH_REDIRECT_URI,
        scope=FLUXER_SCOPE,
    )


@auth_bp.get("/auth")
def auth_callback():
    """
    OAuth callback: exchange code for token, fetch profile + guilds, store in session.
    """
    print(f"[DEBUG] OAuth callback received, provider={OAUTH_PROVIDER}")

    client = oauth.create_client(OAUTH_PROVIDER)
    if client is None:
        print(f"[ERROR] OAuth client not configured for provider {OAUTH_PROVIDER}")
        return jsonify({"detail": f"OAuth provider '{OAUTH_PROVIDER}' not configured"}), 500

    # Exchange authorization code for access token
    try:
        token = client.authorize_access_token()
        access_token = token.get("access_token")
        if not access_token:
            raise ValueError("No access_token received from provider")
    except Exception as e:
        print(f"[ERROR] Token exchange failed: {e}")
        return jsonify({"detail": "Token exchange failed"}), 500

    # Fetch user profile with endpoint fallback for transient provider errors.
    profile = None
    last_error: Exception | None = None
    for profile_url in _build_profile_endpoints():
        try:
            resp = httpx.get(
                profile_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

            # Retry on another endpoint only for provider/server errors.
            if resp.status_code >= 500:
                last_error = RuntimeError(f"{resp.status_code} from {profile_url}")
                continue

            resp.raise_for_status()
            profile = resp.json()
            break
        except Exception as e:
            last_error = e

    if profile is None:
        print(f"[ERROR] Failed to fetch user profile: {last_error}")
        return jsonify({"detail": "Failed to fetch profile"}), 500

    # Fetch guilds
    try:
        guilds_resp = httpx.get(
            "https://api.fluxer.app/v1/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        guilds_resp.raise_for_status()
        guilds = guilds_resp.json()
    except Exception as e:
        print(f"[WARNING] Failed to fetch user guilds: {e}")
        guilds = []

    # Populate session with user info
    session["user"] = {
        "id": profile.get("id"),
        "username": profile.get("username") 
                    or profile.get("preferred_username") 
                    or profile.get("name"),
        "discriminator": profile.get("discriminator"),
        "avatar_url": profile.get("avatar_url") or profile.get("avatar"),
        "guilds": guilds,
    }

    print(f"[DEBUG] OAuth session established for user {session['user']['username']} ({session['user']['id']})")
    redirect_target = FRONTEND_URL if IS_PRODUCTION else "http://localhost:3000"
    return redirect(redirect_target)


@auth_bp.get("/logout")
def logout():
    """
    Clear user session.
    """
    had_user = bool(session.get("user"))
    session.pop("user", None)
    print(f"[DEBUG] Logout endpoint invoked, had_user={had_user}")
    return jsonify({"detail": "logged out"})


@auth_bp.get("/api/me")
@require_user
def get_me():
    """
    Return the authenticated user from the session.
    """
    user = session.get("user")
    # print(f"[DEBUG] /api/me fetched user: {user}")
    return jsonify(user)