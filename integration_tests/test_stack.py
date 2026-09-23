"""The composed stack boots, wires the app to Postgres, and serves the frontend."""


def test_frontend_is_served_from_the_same_origin(base_url):
    import httpx

    response = httpx.get(f"{base_url}/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_docs_are_available(base_url):
    import httpx

    assert httpx.get(f"{base_url}/docs").status_code == 200
    assert httpx.get(f"{base_url}/openapi.json").status_code == 200


def test_pipeline_has_the_single_default_pipeline(client):
    response = client.get("/pipeline")
    assert response.status_code == 200
    assert response.json()["stages"] == ["Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]


def test_empty_postgres_database_is_seeded_on_first_boot(client):
    names = {c["name"] for c in client.get("/contacts").json()}
    assert {"Ava Thompson", "Marcus Lee", "Priya Natarajan", "Diego Ramirez", "Sophie Chen"} <= names

    seeded_deal_titles = {d["title"] for d in client.get("/deals").json()}
    assert "Summit Works platform deal" in seeded_deal_titles


def test_login_rejects_bad_credentials(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_writes_require_a_valid_token(client):
    payload = {"name": "Nobody", "company": "Nowhere"}
    assert client.post("/contacts", json=payload).status_code == 401
    response = client.post("/contacts", json=payload, headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
