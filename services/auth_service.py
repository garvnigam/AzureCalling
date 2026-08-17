import hashlib
import os
import secrets
import time
import uuid
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .logger import get_logger

log = get_logger("auth")

_ALGO = "HS256"
_ITERATIONS = 100_000

# In-memory token cache: token -> expiry (lets us force-logout later if needed)
_token_cache: dict[str, float] = {}

_security = HTTPBearer(auto_error=False)


def _secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        secret = "dev-secret-change-me"
        log.warning("JWT_SECRET not set — using insecure default")
    return secret


# ── Password hashing (stdlib PBKDF2) ────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS,
    )
    return f"pbkdf2${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations),
        )
        return secrets.compare_digest(digest.hex(), expected)
    except Exception:
        return False


# ── Local (hardcoded) users ─────────────────────────────────────────────────
# Temporary username/password logins. Remove once real users are managed.
# IDs are deterministic (uuid5 of the username) so calls attribute correctly.

_LOCAL_CREDENTIALS = {
    "gknsngr7": hash_password("1234"),
    "shyam098": hash_password("abcd"),
}
_LOCAL_NAMES = {
    "gknsngr7": "Gaurav Nigam",
    "shyam098": "Shyam Dubey",
}


def _local_user_id(username: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"local-user:{username}"))


def authenticate_local(username: str, password: str) -> Optional[dict]:
    stored = _LOCAL_CREDENTIALS.get(username)
    if stored is None or not verify_password(password, stored):
        return None
    return {
        "id": _local_user_id(username),
        "username": username,
        "name": _LOCAL_NAMES.get(username, username),
        "source": "local",
    }


def list_local_users() -> list[dict]:
    return [
        {
            "id": _local_user_id(username),
            "email": username,
            "name": _LOCAL_NAMES.get(username, username),
        }
        for username in _LOCAL_CREDENTIALS
    ]


# ── JWT tokens ──────────────────────────────────────────────────────────────

def create_token(user_id: str, email: str, ttl_hours: int = 24, name: str = "") -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + ttl_hours * 3600,
    }
    token = jwt.encode(payload, _secret(), algorithm=_ALGO)
    _token_cache[token] = payload["exp"]
    return token


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("exp") and time.time() > payload["exp"]:
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(credentials.credentials)
    return {"id": payload.get("sub"), "email": payload.get("email"), "name": payload.get("name")}
