"""Add id_counters (race-free id allocation) and auth_tokens (tokens
shared across instances and restarts).

Counters start at the highest number already used for each prefix, so
existing databases keep allocating after their current ids.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ID_PREFIXES = {"c": "contacts", "d": "deals", "a": "activities"}


def upgrade() -> None:
    counters = op.create_table(
        "id_counters",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False),
    )
    op.create_table(
        "auth_tokens",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    connection = op.get_bind()
    rows = []
    for prefix, table in ID_PREFIXES.items():
        ids = connection.execute(sa.text(f"SELECT id FROM {table}")).scalars()
        numbers = [int(i[len(prefix):]) for i in ids if i.startswith(prefix) and i[len(prefix):].isdigit()]
        rows.append({"name": prefix, "value": max(numbers, default=0)})
    op.bulk_insert(counters, rows)


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_table("id_counters")
