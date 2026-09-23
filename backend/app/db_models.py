"""SQLAlchemy ORM tables backing the domain models in models.py.

Tags are stored as a comma-separated string rather than a separate
table -- this is a field on Contact, not a modeled entity, so a plain
column keeps the schema as small as the domain requires.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ContactORM(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    company: Mapped[str] = mapped_column(String, nullable=False)
    job_title: Mapped[str] = mapped_column(String, default="")
    address: Mapped[str] = mapped_column(String, default="")
    website: Mapped[str] = mapped_column(String, default="")
    tags: Mapped[str] = mapped_column(String, default="")


class DealORM(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, default=0)
    stage: Mapped[str] = mapped_column(String, nullable=False)
    expected_close: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ActivityORM(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdCounterORM(Base):
    """Last number handed out per id prefix ("c", "d", "a").

    Bookkeeping for the readable string ids, not a domain entity.
    """

    __tablename__ = "id_counters"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class AuthTokenORM(Base):
    """An issued bearer token. Only its SHA-256 is stored, so a database
    leak doesn't expose usable tokens."""

    __tablename__ = "auth_tokens"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
