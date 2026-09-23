"""Data lives in Postgres, not the app process: it survives an app restart
and the seed isn't re-applied on top of existing data."""
import pytest

pytestmark = pytest.mark.restarts_stack


def test_data_survives_app_restart_without_reseeding(client, auth_headers, make_contact, restart_app):
    contact = make_contact()
    client.post(
        "/activities",
        json={"contactId": contact["id"], "type": "Call", "note": "before restart"},
        headers=auth_headers,
    ).raise_for_status()
    contacts_before = client.get("/contacts").json()

    restart_app()

    assert client.get(f"/contacts/{contact['id']}").json() == contact
    assert [a["note"] for a in client.get(f"/contacts/{contact['id']}/activities").json()] == ["before restart"]
    assert client.get("/contacts").json() == contacts_before


def test_tokens_survive_app_restart(client, auth_headers, restart_app):
    # Tokens are stored in the database (app/auth.py), so a restart or a
    # second instance keeps users logged in.
    restart_app()
    payload = {"name": "After Restart", "company": "Restartco"}
    assert client.post("/contacts", json=payload, headers=auth_headers).status_code == 201
