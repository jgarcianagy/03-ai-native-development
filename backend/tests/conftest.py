import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app import store as store_module
from app.main import app


@pytest.fixture(autouse=True)
def reset_state():
    """Every test gets a fresh, freshly-seeded store and auth store."""
    store_module.reset(store_module.store)
    auth_module.reset(auth_module.auth_store)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
