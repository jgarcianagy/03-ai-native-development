"""Pydantic schemas mirroring the components in openapi.yaml."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class Stage(str, Enum):
    LEAD = "Lead"
    QUALIFIED = "Qualified"
    PROPOSAL = "Proposal"
    NEGOTIATION = "Negotiation"
    WON = "Won"
    LOST = "Lost"


class ActivityType(str, Enum):
    CALL = "Call"
    EMAIL = "Email"
    MEETING = "Meeting"
    NOTE = "Note"


class Pipeline(BaseModel):
    stages: List[Stage]


class Contact(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    company: str
    jobTitle: str
    address: str
    website: str
    tags: List[str]


class ContactInput(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    jobTitle: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    tags: Optional[Union[List[str], str]] = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        return value


class Deal(BaseModel):
    id: str
    contactId: str
    title: str
    value: float
    stage: Stage
    expectedClose: Optional[date] = None
    contactName: Optional[str] = None
    company: Optional[str] = None


class DealInput(BaseModel):
    """`stage` is intentionally a plain string (not the `Stage` enum) so an
    unknown stage name is reported as a 400 `Error` by the store, matching
    openapi.yaml, instead of FastAPI's generic 422 validation error."""

    title: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    contactId: Optional[str] = None
    expectedClose: Optional[date] = None


class Activity(BaseModel):
    id: str
    contactId: str
    type: ActivityType
    note: str
    at: datetime


class ActivityInput(BaseModel):
    """`type` is a plain string for the same reason as `DealInput.stage`
    above: an unknown type should surface as a 400 `Error`, not a 422."""

    contactId: str
    type: str
    note: str
    at: Optional[datetime] = None


class Error(BaseModel):
    error: str


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
