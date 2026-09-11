"""Password hashing and bearer-token authentication.

Uses stdlib PBKDF2 for hashing (no extra native dependency) and opaque
random tokens held in memory, matching the rest of the in-memory store.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_PBKDF2_ITERATIONS = 260_000
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


@dataclass
class AuthStore:
    users: Dict[str, User] = field(default_factory=dict)
    tokens: Dict[str, str] = field(default_factory=dict)  # token -> username

    def add_user(self, username: str, password: str) -> None:
        self.users[username] = User(username=username, password_hash=hash_password(password))

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

    def issue_token(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        self.tokens[token] = username
        return token

    def username_for_token(self, token: str) -> Optional[str]:
        return self.tokens.get(token)


def new_seeded_auth_store() -> AuthStore:
    store = AuthStore()
    store.add_user("admin", "admin123")
    return store


def reset(target: AuthStore) -> None:
    """Reset an existing AuthStore in place. Used by tests so they can share
    the module-level `auth_store` instance that routers import."""
    target.users.clear()
    target.tokens.clear()
    target.add_user("admin", "admin123")


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
