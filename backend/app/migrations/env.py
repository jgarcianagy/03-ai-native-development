"""Alembic environment. The app runs migrations on startup through
app.schema.upgrade_database, which passes in an open connection; the
`alembic` CLI (run from backend/) connects via SDIP_DATABASE_URL instead."""
from alembic import context

from app import db_models  # noqa: F401  (registers the tables on Base.metadata)
from app.database import Base, engine

target_metadata = Base.metadata


def run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    run_migrations(connection)
else:
    with engine.begin() as connection:
        run_migrations(connection)
