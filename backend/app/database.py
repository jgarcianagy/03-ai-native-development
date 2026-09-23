"""Database engine and session configuration.

The connection target is controlled entirely by the SDIP_DATABASE_URL
environment variable, so the same code works against SQLite (the
default, for local/dev use) or any other SQLAlchemy-supported database
(e.g. Postgres) by changing that one value -- no code changes needed.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("SDIP_DATABASE_URL", "sqlite:///./crm.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs = {"connect_args": _connect_args}
if _is_sqlite and ":memory:" in DATABASE_URL:
    # An in-memory SQLite database is per-connection, so without a shared
    # pool every session would see an empty database.
    _engine_kwargs["poolclass"] = StaticPool
if not _is_sqlite:
    # Managed databases (e.g. Cloud SQL) drop idle connections; check each
    # pooled connection before use instead of failing the first request.
    _engine_kwargs["pool_pre_ping"] = True
    # Keep (instances x connections) under small Cloud SQL tiers' limit
    # (db-f1-micro allows 25); deploy/gcp.sh caps instances to match.
    _engine_kwargs["pool_size"] = int(os.environ.get("SDIP_DB_POOL_SIZE", "5"))
    _engine_kwargs["max_overflow"] = int(os.environ.get("SDIP_DB_MAX_OVERFLOW", "2"))

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session, committing on success."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
