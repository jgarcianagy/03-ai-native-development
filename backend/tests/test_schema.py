"""Migrations build the schema the ORM models describe, and upgrade
databases that predate them."""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app import db_models  # noqa: F401
from app.database import Base
from app.schema import upgrade_database


def _schema_diff(engine):
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)


def test_migrations_match_the_orm_models(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    upgrade_database(engine)
    assert _schema_diff(engine) == []


def test_upgrade_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'twice.db'}")
    upgrade_database(engine)
    upgrade_database(engine)
    assert _schema_diff(engine) == []


def test_pre_migration_database_is_stamped_and_upgraded(tmp_path):
    """A database created by the old create_all() keeps its rows, and its
    id counters continue after the ids already in use."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    legacy_tables = [Base.metadata.tables[name] for name in ("contacts", "deals", "activities")]
    Base.metadata.create_all(engine, tables=legacy_tables)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO contacts (id, name, email, phone, company, job_title, address, website, tags) "
                "VALUES ('c7', 'Old Contact', '', '', 'Oldco', '', '', '', '')"
            )
        )

    upgrade_database(engine)

    assert {"id_counters", "auth_tokens", "alembic_version"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM contacts")).scalar_one() == "Old Contact"
        counters = dict(connection.execute(text("SELECT name, value FROM id_counters")).all())
    assert counters == {"c": 7, "d": 0, "a": 0}
