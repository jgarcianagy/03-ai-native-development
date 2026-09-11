def test_login_succeeds_with_seeded_user(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_password(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_login_fails_with_unknown_user(client):
    response = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert response.status_code == 401


def test_create_contact_requires_token(client):
    response = client.post("/api/contacts", json={"name": "New Person", "company": "Acme"})
    assert response.status_code == 401


def test_create_contact_rejects_invalid_token(client):
    response = client.post(
        "/api/contacts",
        json={"name": "New Person", "company": "Acme"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_create_contact_succeeds_with_valid_token(client, auth_headers):
    response = client.post(
        "/api/contacts",
        json={"name": "New Person", "company": "Acme"},
        headers=auth_headers,
    )
    assert response.status_code == 201
