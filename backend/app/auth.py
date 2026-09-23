"""Password hashing and bearer-token authentication.

Uses stdlib PBKDF2 for hashing (no extra native dependency). Users are
the single seeded admin, kept in memory. Tokens are opaque random strings
stored (hashed, with an expiry) in the database, so they work on every
instance and survive restarts.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select

from .database import session_scope
from .db_models import AuthTokenORM

_PBKDF2_ITERATIONS = 260_000
TOKEN_TTL = timedelta(hours=float(os.environ.get("SDIP_TOKEN_TTL_HOURS", "12")))
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


@dataclass
class User:
    username: str
    password_hash: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuthStore:
    users: Dict[str, User] = field(default_factory=dict)

    def add_user(self, username: str, password: str) -> None:
        self.users[username] = User(username=username, password_hash=hash_password(password))

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

    def issue_token(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        with session_scope() as session:
            session.execute(delete(AuthTokenORM).where(AuthTokenORM.expires_at <= now))
            session.add(AuthTokenORM(token_hash=_hash_token(token), username=username, expires_at=now + TOKEN_TTL))
        return token

    def username_for_token(self, token: str) -> Optional[str]:
        with session_scope() as session:
            return session.execute(
                select(AuthTokenORM.username).where(
                    AuthTokenORM.token_hash == _hash_token(token),
                    AuthTokenORM.expires_at > _now(),
                )
            ).scalar_one_or_none()


def new_seeded_auth_store() -> AuthStore:
    store = AuthStore()
    store.add_user("admin", "admin123")
    return store


def reset(target: AuthStore) -> None:
    """Reset an existing AuthStore in place. Used by tests so they can share
    the module-level `auth_store` instance that routers import."""
    target.users.clear()
    target.add_user("admin", "admin123")
    with session_scope() as session:
        session.execute(delete(AuthTokenORM))


auth_store = new_seeded_auth_store()


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency: validates the bearer token, returns the username."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = auth_store.username_for_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username
