"""SQLAlchemy-backed data store for contacts, deals, and activities.

Persistence goes through whichever database SDIP_DATABASE_URL (see
app.database) points at. Each method opens and commits its own short
session so the module-level `store` instance below can be shared across
requests the same way the previous in-memory store was.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from . import models, schema
from .database import Base, engine, session_scope
from .db_models import ActivityORM, ContactORM, DealORM, IdCounterORM
from .errors import NotFoundError, ValidationError

PIPELINE_STAGES: List[str] = [s.value for s in models.Stage]
ACTIVITY_TYPES: List[str] = [t.value for t in models.ActivityType]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _split_tags(raw: str) -> List[str]:
    return [tag for tag in raw.split(",") if tag] if raw else []


def _join_tags(tags: List[str]) -> str:
    return ",".join(tags)


def _next_id(session: Session, prefix: str) -> str:
    """Allocate the next `{prefix}{n}` id from the prefix's row in id_counters.

    The UPDATE locks that row until the transaction commits, so concurrent
    creates (across threads or instances) always get distinct numbers.
    """
    value = session.execute(
        update(IdCounterORM)
        .where(IdCounterORM.name == prefix)
        .values(value=IdCounterORM.value + 1)
        .returning(IdCounterORM.value)
    ).scalar_one_or_none()
    if value is None:
        raise RuntimeError(f"No id counter for prefix {prefix!r}; run the database migrations")
    return f"{prefix}{value}"


def _contact_to_model(row: ContactORM) -> models.Contact:
    return models.Contact(
        id=row.id,
        name=row.name,
        email=row.email,
        phone=row.phone,
        company=row.company,
        jobTitle=row.job_title,
        address=row.address,
        website=row.website,
        tags=_split_tags(row.tags),
    )


def _activity_to_model(row: ActivityORM) -> models.Activity:
    return models.Activity(
        id=row.id,
        contactId=row.contact_id,
        type=models.ActivityType(row.type),
        note=row.note,
        at=row.at,
    )


class Store:
    # ---- pipeline -----------------------------------------------------

    def get_pipeline(self) -> models.Pipeline:
        return models.Pipeline(stages=list(models.Stage))

    # ---- contacts -------------------------------------------------------

    def list_contacts(
        self, search: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[models.Contact]:
        with session_scope() as session:
            rows = session.execute(select(ContactORM)).scalars().all()
            results = [_contact_to_model(r) for r in rows]

        if search:
            needle = search.lower()
            results = [
                c
                for c in results
                if needle in c.name.lower()
                or needle in c.email.lower()
                or needle in c.company.lower()
            ]
        if tags:
            required = {t.strip() for t in tags if t.strip()}
            results = [c for c in results if required.issubset(set(c.tags))]
        return sorted(results, key=lambda c: c.name.lower())

    def _get_contact_row(self, session: Session, contact_id: str) -> ContactORM:
        row = session.get(ContactORM, contact_id)
        if row is None:
            raise NotFoundError(f"No contact with id {contact_id}")
        return row

    def get_contact(self, contact_id: str) -> models.Contact:
        with session_scope() as session:
            return _contact_to_model(self._get_contact_row(session, contact_id))

    def create_contact(self, data: models.ContactInput) -> models.Contact:
        if not data.name or not data.name.strip():
            raise ValidationError("Contact name is required")
        if not data.company or not data.company.strip():
            raise ValidationError("Contact company is required")

        with session_scope() as session:
            contact_id = _next_id(session, "c")
            row = ContactORM(
                id=contact_id,
                name=data.name.strip(),
                email=(data.email or "").strip(),
                phone=(data.phone or "").strip(),
                company=data.company.strip(),
                job_title=(data.jobTitle or "").strip(),
                address=(data.address or "").strip(),
                website=(data.website or "").strip(),
                tags=_join_tags(list(data.tags or [])),
            )
            session.add(row)
            session.flush()
            return _contact_to_model(row)

    def update_contact(self, contact_id: str, patch: models.ContactInput) -> models.Contact:
        update = patch.model_dump(exclude_unset=True)

        with session_scope() as session:
            row = self._get_contact_row(session, contact_id)

            if "name" in update:
                if not update["name"] or not update["name"].strip():
                    raise ValidationError("Contact name is required")
                row.name = update["name"].strip()
            if "company" in update:
                if not update["company"] or not update["company"].strip():
                    raise ValidationError("Contact company is required")
                row.company = update["company"].strip()
            if "email" in update:
                row.email = update["email"] or ""
            if "phone" in update:
                row.phone = update["phone"] or ""
            if "jobTitle" in update:
                row.job_title = update["jobTitle"] or ""
            if "address" in update:
                row.address = update["address"] or ""
            if "website" in update:
                row.website = update["website"] or ""
            if "tags" in update:
                row.tags = _join_tags(list(update["tags"] or []))

            session.flush()
            return _contact_to_model(row)

    def list_tags(self) -> List[str]:
        with session_scope() as session:
            raw_values = session.execute(select(ContactORM.tags)).scalars().all()
        tags = {tag for raw in raw_values for tag in _split_tags(raw)}
        return sorted(tags)

    # ---- deals ------------------------------------------------------------

    def _enrich_deal(self, session: Session, row: DealORM) -> models.Deal:
        contact = session.get(ContactORM, row.contact_id)
        return models.Deal(
            id=row.id,
            contactId=row.contact_id,
            title=row.title,
            value=row.value,
            stage=models.Stage(row.stage),
            expectedClose=row.expected_close,
            contactName=contact.name if contact else None,
            company=contact.company if contact else None,
        )

    def list_deals(
        self, contact_id: Optional[str] = None, stage: Optional[str] = None
    ) -> List[models.Deal]:
        with session_scope() as session:
            stmt = select(DealORM)
            if contact_id:
                stmt = stmt.where(DealORM.contact_id == contact_id)
            if stage:
                stmt = stmt.where(DealORM.stage == stage)
            rows = session.execute(stmt).scalars().all()
            return [self._enrich_deal(session, r) for r in rows]

    def get_deal(self, deal_id: str) -> models.Deal:
        with session_scope() as session:
            row = session.get(DealORM, deal_id)
            if row is None:
                raise NotFoundError(f"No deal with id {deal_id}")
            return self._enrich_deal(session, row)

    def create_deal(self, data: models.DealInput) -> models.Deal:
        if not data.contactId:
            raise ValidationError("A deal must belong to a contact")
        if not data.title or not data.title.strip():
            raise ValidationError("Deal title is required")

        stage_value = data.stage or models.Stage.LEAD.value
        if stage_value not in PIPELINE_STAGES:
            raise ValidationError(f"Unknown stage: {stage_value}")

        with session_scope() as session:
            contact = session.get(ContactORM, data.contactId)
            if contact is None:
                raise ValidationError(f"No contact with id {data.contactId}")

            deal_id = _next_id(session, "d")
            row = DealORM(
                id=deal_id,
                contact_id=data.contactId,
                title=data.title.strip(),
                value=data.value or 0,
                stage=stage_value,
                expected_close=data.expectedClose,
            )
            session.add(row)
            session.flush()
            return self._enrich_deal(session, row)

    def update_deal(self, deal_id: str, patch: models.DealInput) -> models.Deal:
        update = patch.model_dump(exclude_unset=True)

        with session_scope() as session:
            row = session.get(DealORM, deal_id)
            if row is None:
                raise NotFoundError(f"No deal with id {deal_id}")

            if "contactId" in update:
                new_contact_id = update["contactId"]
                if not new_contact_id:
                    raise ValidationError("A deal must belong to a contact")
                if session.get(ContactORM, new_contact_id) is None:
                    raise ValidationError(f"No contact with id {new_contact_id}")
                row.contact_id = new_contact_id

            if "title" in update:
                if not update["title"] or not update["title"].strip():
                    raise ValidationError("Deal title is required")
                row.title = update["title"].strip()

            if "stage" in update:
                stage_value = update["stage"]
                if stage_value not in PIPELINE_STAGES:
                    raise ValidationError(f"Unknown stage: {stage_value}")
                row.stage = stage_value

            if "value" in update:
                row.value = update["value"] or 0

            if "expectedClose" in update:
                row.expected_close = update["expectedClose"]

            session.flush()
            return self._enrich_deal(session, row)

    # ---- activities ---------------------------------------------------

    def list_activities(self, contact_id: str) -> List[models.Activity]:
        with session_scope() as session:
            if session.get(ContactORM, contact_id) is None:
                raise NotFoundError(f"No contact with id {contact_id}")
            stmt = select(ActivityORM).where(ActivityORM.contact_id == contact_id)
            rows = session.execute(stmt).scalars().all()
            results = [_activity_to_model(r) for r in rows]
        return sorted(results, key=lambda a: a.at, reverse=True)

    def create_activity(self, data: models.ActivityInput) -> models.Activity:
        if not data.contactId:
            raise ValidationError("An activity must belong to a contact")
        if data.type not in ACTIVITY_TYPES:
            raise ValidationError(f"Unknown activity type: {data.type}")
        if not data.note or not data.note.strip():
            raise ValidationError("Activity note is required")

        with session_scope() as session:
            if session.get(ContactORM, data.contactId) is None:
                raise ValidationError(f"No contact with id {data.contactId}")

            activity_id = _next_id(session, "a")
            row = ActivityORM(
                id=activity_id,
                contact_id=data.contactId,
                type=data.type,
                note=data.note.strip(),
                at=data.at or _now(),
            )
            session.add(row)
            session.flush()
            return _activity_to_model(row)


def seed(store: Store) -> None:
    """Populate the store with a handful of contacts, deals, and activities."""

    contacts_seed = [
        dict(
            name="Ava Thompson",
            email="ava.thompson@brightline.com",
            phone="+1-555-0101",
            company="Brightline Co",
            jobTitle="VP of Sales",
            address="100 Market St, San Francisco, CA",
            website="https://brightline.example.com",
            tags=["vip", "west-coast"],
        ),
        dict(
            name="Marcus Lee",
            email="marcus.lee@northfield.io",
            phone="+1-555-0102",
            company="Northfield Industries",
            jobTitle="Procurement Manager",
            address="55 Harbor Rd, Boston, MA",
            website="https://northfield.example.com",
            tags=["east-coast"],
        ),
        dict(
            name="Priya Natarajan",
            email="priya.n@summitworks.com",
            phone="+1-555-0103",
            company="Summit Works",
            jobTitle="CEO",
            address="12 Ridge Ave, Denver, CO",
            website="https://summitworks.example.com",
            tags=["vip", "decision-maker"],
        ),
        dict(
            name="Diego Ramirez",
            email="d.ramirez@lumenretail.com",
            phone="+1-555-0104",
            company="Lumen Retail",
            jobTitle="Operations Lead",
            address="9 Canal St, Austin, TX",
            website="https://lumenretail.example.com",
            tags=["retail"],
        ),
        dict(
            name="Sophie Chen",
            email="sophie.chen@harborhealth.org",
            phone="+1-555-0105",
            company="Harbor Health",
            jobTitle="IT Director",
            address="200 Bayview Dr, Seattle, WA",
            website="https://harborhealth.example.com",
            tags=["healthcare", "west-coast"],
        ),
    ]

    contacts: List[models.Contact] = []
    for entry in contacts_seed:
        contact = store.create_contact(models.ContactInput(**entry))
        contacts.append(contact)

    deals_seed = [
        dict(contact=0, title="Brightline Q3 renewal", value=42000, stage="Qualified", expectedClose="2026-09-30"),
        dict(contact=0, title="Brightline expansion pack", value=15000, stage="Lead", expectedClose="2026-11-15"),
        dict(contact=1, title="Northfield onboarding", value=8000, stage="Proposal", expectedClose="2026-10-01"),
        dict(contact=2, title="Summit Works platform deal", value=120000, stage="Negotiation", expectedClose="2026-09-20"),
        dict(contact=3, title="Lumen Retail pilot", value=5000, stage="Won", expectedClose="2026-08-01"),
        dict(contact=4, title="Harbor Health security review", value=25000, stage="Lost", expectedClose="2026-07-15"),
    ]
    for entry in deals_seed:
        contact = contacts[entry["contact"]]
        store.create_deal(
            models.DealInput(
                contactId=contact.id,
                title=entry["title"],
                value=entry["value"],
                stage=entry["stage"],
                expectedClose=date.fromisoformat(entry["expectedClose"]),
            )
        )

    activities_seed = [
        dict(contact=0, type="Call", note="Discussed renewal terms.", at="2026-09-01T15:00:00Z"),
        dict(contact=0, type="Email", note="Sent updated proposal.", at="2026-09-03T09:30:00Z"),
        dict(contact=1, type="Meeting", note="Kickoff meeting with procurement team.", at="2026-08-20T14:00:00Z"),
        dict(contact=2, type="Note", note="Prefers async updates over calls.", at="2026-08-15T11:00:00Z"),
        dict(contact=3, type="Call", note="Confirmed pilot success, moving to Won.", at="2026-08-01T16:00:00Z"),
        dict(contact=4, type="Meeting", note="Lost to competitor on pricing.", at="2026-07-15T10:00:00Z"),
    ]
    for entry in activities_seed:
        contact = contacts[entry["contact"]]
        store.create_activity(
            models.ActivityInput(
                contactId=contact.id,
                type=entry["type"],
                note=entry["note"],
                at=datetime.fromisoformat(entry["at"].replace("Z", "+00:00")),
            )
        )


ID_PREFIXES = ("c", "d", "a")

# Production sets this to "false" so the demo contacts and deals never land
# in a real database.
SEED_DEMO_DATA = os.environ.get("SDIP_SEED_DEMO_DATA", "true").lower() != "false"


def init_db() -> None:
    """Run any pending schema migrations. Safe to call repeatedly."""
    schema.upgrade_database(engine)


def _is_empty(session: Session) -> bool:
    return session.execute(select(ContactORM.id).limit(1)).first() is None


def new_seeded_store() -> Store:
    """Return a Store bound to the configured database.

    Demo data is seeded only if enabled and the database is currently
    empty, so restarting the app against a persistent database doesn't
    wipe existing data.
    """
    init_db()
    result = Store()
    if SEED_DEMO_DATA:
        with session_scope() as session:
            empty = _is_empty(session)
        if empty:
            seed(result)
    return result


def reset(target: Store) -> None:
    """Empty all tables and reseed. Used by tests so they can share the
    module-level `store` instance that routers import."""
    with session_scope() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.add_all(IdCounterORM(name=prefix, value=0) for prefix in ID_PREFIXES)
    seed(target)


store = new_seeded_store()
