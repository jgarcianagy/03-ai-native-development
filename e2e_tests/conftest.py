"""Browser end-to-end tests: drive the real frontend (served by the app
container) against the real API and Postgres.

These tests don't manage the stack; start one first (`make test-e2e` does
it for you). Environment:

- CRM_BASE_URL: the running app, default http://localhost:18001 (the
  integration-test stack's port).
"""
from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("CRM_BASE_URL", "http://localhost:18001").rstrip("/")


@pytest.fixture(scope="session")
def app_url() -> str:
    deadline = time.monotonic() + 90
    while True:
        try:
            if httpx.get(f"{BASE_URL}/api/health", timeout=2).status_code == 200:
                return BASE_URL
        except httpx.HTTPError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError(f"App at {BASE_URL} is not healthy")
        time.sleep(0.5)


@pytest.fixture(scope="session")
def api(app_url):
    with httpx.Client(base_url=f"{app_url}/api", timeout=10) as client:
        token = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.fixture
def unique() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def contact(api, unique) -> dict:
    """A contact created through the API, for tests that start from one."""
    response = api.post(
        "/contacts",
        json={"name": f"E2E Person {unique}", "email": f"e2e.{unique}@example.com", "company": f"E2E Co {unique}"},
    )
    response.raise_for_status()
    return response.json()


@pytest.fixture
def open_contact(page, app_url):
    """Load the app, search for a contact and open it."""

    def _open(contact: dict) -> None:
        page.goto(app_url)
        page.get_by_label("Search contacts").fill(contact["company"])
        page.get_by_role("button", name=contact["name"]).click()
        page.get_by_role("heading", level=2, name=contact["name"]).wait_for()

    return _open
