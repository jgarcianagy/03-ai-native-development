def test_create_activity_requires_auth(client):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/activities",
        json={"contactId": contacts[0]["id"], "type": "Call", "note": "Hi"},
    )
    assert response.status_code == 401


def test_create_activity_succeeds(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/activities",
        json={"contactId": contacts[0]["id"], "type": "Call", "note": "Follow-up call"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["contactId"] == contacts[0]["id"]
    assert body["type"] == "Call"
    assert body["at"]


def test_create_activity_defaults_at_to_now(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/activities",
        json={"contactId": contacts[0]["id"], "type": "Note", "note": "No timestamp given"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["at"] is not None


def test_create_activity_rejects_missing_contact(client, auth_headers):
    response = client.post(
        "/api/activities",
        json={"contactId": "does-not-exist", "type": "Call", "note": "Hi"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_activity_rejects_unknown_type(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/activities",
        json={"contactId": contacts[0]["id"], "type": "Carrier Pigeon", "note": "Hi"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_activity_rejects_blank_note(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/activities",
        json={"contactId": contacts[0]["id"], "type": "Call", "note": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_new_activity_appears_in_contact_history(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    contact_id = contacts[0]["id"]
    before = client.get(f"/api/contacts/{contact_id}/activities").json()

    client.post(
        "/api/activities",
        json={"contactId": contact_id, "type": "Meeting", "note": "New meeting"},
        headers=auth_headers,
    )

    after = client.get(f"/api/contacts/{contact_id}/activities").json()
    assert len(after) == len(before) + 1
