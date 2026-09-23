"""Behaviour that production relies on: ids never collide under concurrent
writes, tokens live in the database, and CORS can be switched off."""
import importlib
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import update

from app import auth as auth_module
from app import models
from app import store as store_module
from app.database import session_scope
from app.db_models import AuthTokenORM


def test_concurrent_creates_get_distinct_ids():
    def create(i: int) -> str:
        return store_module.store.create_contact(models.ContactInput(name=f"Parallel {i}", company="Parallel Inc")).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(create, range(24)))

    assert len(set(ids)) == 24


def test_ids_continue_after_the_seeded_ones():
    contact = store_module.store.create_contact(models.ContactInput(name="Next", company="Nextco"))
    assert contact.id == "c6"  # the seed creates c1..c5


def test_tokens_are_stored_hashed_not_in_plain_text(auth_headers):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    with session_scope() as session:
        hashes = [row.token_hash for row in session.query(AuthTokenORM).all()]
    assert hashes and token not in hashes


def test_tokens_survive_a_new_auth_store(client, auth_headers, monkeypatch):
    """A token issued by one process is accepted by another (instances and restarts)."""
    monkeypatch.setattr(auth_module, "auth_store", auth_module.new_seeded_auth_store())
    username = auth_module.auth_store.username_for_token(auth_headers["Authorization"].removeprefix("Bearer "))
    assert username == "admin"


def test_expired_tokens_are_rejected(client, auth_headers):
    with session_scope() as session:
        session.execute(update(AuthTokenORM).values(expires_at=auth_module._now() - auth_module.TOKEN_TTL))
    response = client.post("/api/contacts", json={"name": "Late", "company": "Lateco"}, headers=auth_headers)
    assert response.status_code == 401


def test_demo_seed_can_be_disabled(monkeypatch):
    monkeypatch.setattr(store_module, "SEED_DEMO_DATA", False)
    with session_scope() as session:
        for table in ("activities", "deals", "contacts"):
            session.execute(store_module.Base.metadata.tables[table].delete())
    store_module.new_seeded_store()
    assert store_module.store.list_contacts() == []


def test_cors_is_off_when_origins_are_empty(monkeypatch):
    from app import main

    monkeypatch.setenv("SDIP_CORS_ORIGINS", "")
    try:
        reloaded = importlib.reload(main)
        assert not any(m.cls.__name__ == "CORSMiddleware" for m in reloaded.app.user_middleware)
    finally:
        monkeypatch.delenv("SDIP_CORS_ORIGINS")
        importlib.reload(main)
