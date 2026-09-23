from sqlalchemy.exc import OperationalError

from app import database


def test_health_reports_ok_when_database_is_reachable(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "dev"}


def test_health_is_503_when_database_is_unreachable(client, monkeypatch):
    class BrokenEngine:
        def connect(self):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(database, "engine", BrokenEngine())
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
