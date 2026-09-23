"""Initial schema: contacts, deals, activities.

Matches the tables that app.store created with create_all() before
migrations were introduced; app.schema stamps such databases with this
revision instead of re-creating the tables.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("job_title", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("website", sa.String(), nullable=False),
        sa.Column("tags", sa.String(), nullable=False),
    )
    op.create_table(
        "deals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contact_id", sa.String(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("expected_close", sa.Date(), nullable=True),
    )
    op.create_table(
        "activities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contact_id", sa.String(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("activities")
    op.drop_table("deals")
    op.drop_table("contacts")
