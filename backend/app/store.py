"""In-memory data store for contacts, deals, and activities.

A plain dict-backed store is enough for this MVP (no persistence, no
concurrency concerns beyond FastAPI's single-process dev usage).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from . import models
from .errors import NotFoundError, ValidationError

PIPELINE_STAGES: List[str] = [s.value for s in models.Stage]
ACTIVITY_TYPES: List[str] = [t.value for t in models.ActivityType]


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Store:
    contacts: Dict[str, models.Contact] = field(default_factory=dict)
    deals: Dict[str, models.Deal] = field(default_factory=dict)
    activities: Dict[str, models.Activity] = field(default_factory=dict)
    _contact_ids: "itertools.count" = field(default_factory=lambda: itertools.count(1))
    _deal_ids: "itertools.count" = field(default_factory=lambda: itertools.count(1))
    _activity_ids: "itertools.count" = field(default_factory=lambda: itertools.count(1))

    # ---- pipeline -----------------------------------------------------

    def get_pipeline(self) -> models.Pipeline:
        return models.Pipeline(stages=list(models.Stage))

    # ---- contacts -------------------------------------------------------

    def list_contacts(
        self, search: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[models.Contact]:
        results = list(self.contacts.values())
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

    def get_contact(self, contact_id: str) -> models.Contact:
        contact = self.contacts.get(contact_id)
        if contact is None:
            raise NotFoundError(f"No contact with id {contact_id}")
        return contact

    def create_contact(self, data: models.ContactInput) -> models.Contact:
        if not data.name or not data.name.strip():
            raise ValidationError("Contact name is required")
        if not data.company or not data.company.strip():
            raise ValidationError("Contact company is required")

        contact_id = f"c{next(self._contact_ids)}"
        contact = models.Contact(
            id=contact_id,
            name=data.name.strip(),
            email=(data.email or "").strip(),
            phone=(data.phone or "").strip(),
            company=data.company.strip(),
            jobTitle=(data.jobTitle or "").strip(),
            address=(data.address or "").strip(),
            website=(data.website or "").strip(),
            tags=list(data.tags or []),
        )
        self.contacts[contact_id] = contact
        return contact

    def update_contact(self, contact_id: str, patch: models.ContactInput) -> models.Contact:
        contact = self.get_contact(contact_id)

        update = patch.model_dump(exclude_unset=True)
        if "name" in update:
            if not update["name"] or not update["name"].strip():
                raise ValidationError("Contact name is required")
            contact.name = update["name"].strip()
        if "company" in update:
            if not update["company"] or not update["company"].strip():
                raise ValidationError("Contact company is required")
            contact.company = update["company"].strip()
        if "email" in update:
            contact.email = update["email"] or ""
        if "phone" in update:
            contact.phone = update["phone"] or ""
        if "jobTitle" in update:
            contact.jobTitle = update["jobTitle"] or ""
        if "address" in update:
            contact.address = update["address"] or ""
        if "website" in update:
            contact.website = update["website"] or ""
        if "tags" in update:
            contact.tags = list(update["tags"] or [])

        self.contacts[contact_id] = contact
        self._sync_denormalized_deal_fields(contact)
        return contact

    def list_tags(self) -> List[str]:
        tags = {tag for contact in self.contacts.values() for tag in contact.tags}
        return sorted(tags)

    # ---- deals ------------------------------------------------------------

    def _sync_denormalized_deal_fields(self, contact: models.Contact) -> None:
        for deal in self.deals.values():
            if deal.contactId == contact.id:
                deal.contactName = contact.name
                deal.company = contact.company

    def _enrich_deal(self, deal: models.Deal) -> models.Deal:
        contact = self.contacts.get(deal.contactId)
        if contact is not None:
            deal.contactName = contact.name
            deal.company = contact.company
        return deal

    def list_deals(
        self, contact_id: Optional[str] = None, stage: Optional[str] = None
    ) -> List[models.Deal]:
        results = list(self.deals.values())
        if contact_id:
            results = [d for d in results if d.contactId == contact_id]
        if stage:
            results = [d for d in results if d.stage.value == stage]
        return [self._enrich_deal(d) for d in results]

    def get_deal(self, deal_id: str) -> models.Deal:
        deal = self.deals.get(deal_id)
        if deal is None:
            raise NotFoundError(f"No deal with id {deal_id}")
        return self._enrich_deal(deal)

    def create_deal(self, data: models.DealInput) -> models.Deal:
        if not data.contactId:
            raise ValidationError("A deal must belong to a contact")
        contact = self.contacts.get(data.contactId)
        if contact is None:
            raise ValidationError(f"No contact with id {data.contactId}")
        if not data.title or not data.title.strip():
            raise ValidationError("Deal title is required")

        stage_value = data.stage or models.Stage.LEAD.value
        if stage_value not in PIPELINE_STAGES:
            raise ValidationError(f"Unknown stage: {stage_value}")

        deal_id = f"d{next(self._deal_ids)}"
        deal = models.Deal(
            id=deal_id,
            contactId=data.contactId,
            title=data.title.strip(),
            value=data.value or 0,
            stage=models.Stage(stage_value),
            expectedClose=data.expectedClose,
            contactName=contact.name,
            company=contact.company,
        )
        self.deals[deal_id] = deal
        return deal

    def update_deal(self, deal_id: str, patch: models.DealInput) -> models.Deal:
        deal = self.deals.get(deal_id)
        if deal is None:
            raise NotFoundError(f"No deal with id {deal_id}")

        update = patch.model_dump(exclude_unset=True)

        if "contactId" in update:
            new_contact_id = update["contactId"]
            if not new_contact_id:
                raise ValidationError("A deal must belong to a contact")
            contact = self.contacts.get(new_contact_id)
            if contact is None:
                raise ValidationError(f"No contact with id {new_contact_id}")
            deal.contactId = new_contact_id

        if "title" in update:
            if not update["title"] or not update["title"].strip():
                raise ValidationError("Deal title is required")
            deal.title = update["title"].strip()

        if "stage" in update:
            stage_value = update["stage"]
            if stage_value not in PIPELINE_STAGES:
                raise ValidationError(f"Unknown stage: {stage_value}")
            deal.stage = models.Stage(stage_value)

        if "value" in update:
            deal.value = update["value"] or 0

        if "expectedClose" in update:
            deal.expectedClose = update["expectedClose"]

        self.deals[deal_id] = deal
        return self._enrich_deal(deal)

    # ---- activities ---------------------------------------------------

    def list_activities(self, contact_id: str) -> List[models.Activity]:
        self.get_contact(contact_id)  # raises NotFoundError if missing
        results = [a for a in self.activities.values() if a.contactId == contact_id]
        return sorted(results, key=lambda a: a.at, reverse=True)

    def create_activity(self, data: models.ActivityInput) -> models.Activity:
        if not data.contactId:
            raise ValidationError("An activity must belong to a contact")
        if self.contacts.get(data.contactId) is None:
            raise ValidationError(f"No contact with id {data.contactId}")
        if data.type not in ACTIVITY_TYPES:
            raise ValidationError(f"Unknown activity type: {data.type}")
        if not data.note or not data.note.strip():
            raise ValidationError("Activity note is required")

        activity_id = f"a{next(self._activity_ids)}"
        activity = models.Activity(
            id=activity_id,
            contactId=data.contactId,
            type=models.ActivityType(data.type),
            note=data.note.strip(),
            at=data.at or _now(),
        )
        self.activities[activity_id] = activity
        return activity


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


def new_seeded_store() -> Store:
    store = Store()
    seed(store)
    return store


def reset(target: Store) -> None:
    """Reset an existing Store in place and reseed it. Used by tests so they
    can share the module-level `store` instance that routers import."""
    target.contacts.clear()
    target.deals.clear()
    target.activities.clear()
    target._contact_ids = itertools.count(1)
    target._deal_ids = itertools.count(1)
    target._activity_ids = itertools.count(1)
    seed(target)


store = new_seeded_store()
