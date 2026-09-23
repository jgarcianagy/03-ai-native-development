"""Brings the database schema up to date by running the Alembic
migrations in app/migrations. Called on app startup."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
# Tables created with create_all() before migrations existed match this revision.
BASELINE_REVISION = "0001"
# Arbitrary constant: serializes migrations when several instances start at once.
_ADVISORY_LOCK_KEY = 72_031_001


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def upgrade_database(engine: Engine) -> None:
    config = alembic_config()
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ADVISORY_LOCK_KEY})
        config.attributes["connection"] = connection
        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables and "contacts" in tables:
            command.stamp(config, BASELINE_REVISION)
        command.upgrade(config, "head")
