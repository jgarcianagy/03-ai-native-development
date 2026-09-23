"""Integration tests that run against the real docker-compose stack
(Postgres + the built app image), talking to it over HTTP.

By default the suite brings up its own isolated compose project (separate
name, host port and volume), and tears it down afterwards. Environment:

- CRM_BASE_URL: run against an already-running stack instead; the suite
  won't start, stop or restart anything.
- CRM_IT_KEEP=1: leave the stack running after the suite, for debugging.
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT_NAME = "crm-integration-tests"
COMPOSE_FILES = [REPO_ROOT / "docker-compose.yaml", Path(__file__).parent / "docker-compose.test.yaml"]
DEFAULT_BASE_URL = "http://localhost:18001"

EXTERNAL_BASE_URL = os.environ.get("CRM_BASE_URL")


def compose(*args: str) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", "-p", PROJECT_NAME]
    for f in COMPOSE_FILES:
        cmd += ["-f", str(f)]
    return subprocess.run(cmd + list(args), cwd=REPO_ROOT, check=True, capture_output=True, text=True)


def wait_until_ready(base_url: str, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/api/pipeline", timeout=2).status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"App at {base_url} did not become ready: {last_error}")


@pytest.fixture(scope="session")
def base_url():
    if EXTERNAL_BASE_URL:
        wait_until_ready(EXTERNAL_BASE_URL)
        yield EXTERNAL_BASE_URL
        return

    # Start from an empty database every run so seeding is exercised.
    compose("down", "-v", "--remove-orphans")
    try:
        compose("up", "-d", "--build")
        wait_until_ready(DEFAULT_BASE_URL)
    except Exception:
        print(compose("logs", "--no-color").stdout)
        compose("down", "-v")
        raise
    yield DEFAULT_BASE_URL
    if not os.environ.get("CRM_IT_KEEP"):
        compose("down", "-v")


@pytest.fixture
def restart_app(base_url):
    """Restart only the app container, keeping the Postgres volume."""
    if EXTERNAL_BASE_URL:
        pytest.skip("won't restart an external stack")

    def _restart() -> None:
        compose("restart", "app")
        wait_until_ready(base_url)

    return _restart


@pytest.fixture
def client(base_url):
    with httpx.Client(base_url=f"{base_url}/api", timeout=10) as c:
        yield c


def login(client: httpx.Client) -> dict:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return login(client)


@pytest.fixture
def unique():
    """Short unique suffix so tests don't collide on shared database state."""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def make_contact(client, auth_headers, unique):
    def _make(**overrides) -> dict:
        payload = {
            "name": f"Test Person {unique}",
            "email": f"test.{unique}@example.com",
            "company": f"Testco {unique}",
            **overrides,
        }
        response = client.post("/contacts", json=payload, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
