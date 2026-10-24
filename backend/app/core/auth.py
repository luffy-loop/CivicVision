"""Small, dependency-free authority sessions for configured named staff accounts."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Header, HTTPException

from app.core.config import get_settings

PBKDF2_ROUNDS = 310_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ROUNDS,
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt_bytes = base64.urlsafe_b64decode(salt + "=" * (-len(salt) % 4))
        expected_bytes = base64.urlsafe_b64decode(expected + "=" * (-len(expected) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, int(rounds))
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, TypeError):
        return False


def _users() -> dict[str, dict[str, str]]:
    settings = get_settings()
    try:
        users: Any = json.loads(settings.authority_users)
    except (ValueError, TypeError):
        return {}
    if not isinstance(users, list):
        return {}
    return {
        item["username"]: item
        for item in users
        if isinstance(item, dict)
        and isinstance(item.get("username"), str)
        and isinstance(item.get("password_hash"), str)
        and item.get("role") in {"reviewer", "admin"}
    }


def configuration_ready() -> bool:
    settings = get_settings()
    return len(settings.auth_token_secret.encode()) >= 32 and bool(_users())


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def issue_token(username: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    ttl = max(5, min(settings.auth_token_ttl_minutes, 1440)) * 60
    payload = _b64(json.dumps({"sub": username, "role": role, "exp": int(time.time()) + ttl}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.auth_token_secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", ttl


def get_authority(authorization: str | None = Header(None)) -> dict[str, str]:
    if not configuration_ready():
        raise HTTPException(status_code=503, detail="Authority access is not configured. Set AUTHORITY_USERS and AUTH_TOKEN_SECRET.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in with an authority account to continue.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload, signature = authorization[7:].split(".", 1)
        settings = get_settings()
        expected = _b64(hmac.new(settings.auth_token_secret.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(claims["exp"]) <= int(time.time()) or claims["role"] not in {"reviewer", "admin"}:
            raise ValueError("expiry or role")
        return {"username": str(claims["sub"]), "role": str(claims["role"])}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Authority session is invalid or expired.", headers={"WWW-Authenticate": "Bearer"})


def require_admin(user: dict[str, str]) -> dict[str, str]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user
