"""Record an interaction and see it in the contact's history."""
import pytest


@pytest.mark.parametrize("activity_type", ["Call", "Email", "Meeting", "Note"])
def test_each_activity_type_is_saved_to_contact_history(client, auth_headers, make_contact, activity_type):
    contact = make_contact()
    response = client.post(
        "/activities",
        json={"contactId": contact["id"], "type": activity_type, "note": f"A {activity_type}"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text

    history = client.get(f"/contacts/{contact['id']}/activities").json()
    assert [(a["type"], a["note"]) for a in history] == [(activity_type, f"A {activity_type}")]


def test_history_is_newest_first_and_timestamps_round_trip(client, auth_headers, make_contact):
    contact = make_contact()
    for at, note in [("2026-01-01T09:00:00+00:00", "older"), ("2026-03-01T17:30:00+02:00", "newer")]:
        client.post(
            "/activities",
            json={"contactId": contact["id"], "type": "Note", "note": note, "at": at},
            headers=auth_headers,
        ).raise_for_status()

    history = client.get(f"/contacts/{contact['id']}/activities").json()
    assert [a["note"] for a in history] == ["newer", "older"]
    # Postgres timestamptz preserves the instant (15:30 UTC == 17:30 +02:00).
    from datetime import datetime, timezone

    newer_at = datetime.fromisoformat(history[0]["at"].replace("Z", "+00:00"))
    assert newer_at.astimezone(timezone.utc) == datetime(2026, 3, 1, 15, 30, tzinfo=timezone.utc)


def test_activities_are_scoped_to_their_contact(client, auth_headers, make_contact, unique):
    first = make_contact(name=f"First {unique}")
    second = make_contact(name=f"Second {unique}")
    client.post(
        "/activities",
        json={"contactId": first["id"], "type": "Call", "note": "only for first"},
        headers=auth_headers,
    ).raise_for_status()

    assert client.get(f"/contacts/{second['id']}/activities").json() == []


def test_activity_rejects_unknown_type_and_missing_contact(client, auth_headers, make_contact):
    contact = make_contact()
    response = client.post(
        "/activities",
        json={"contactId": contact["id"], "type": "Task", "note": "x"},
        headers=auth_headers,
    )
    assert response.status_code == 400

    response = client.post(
        "/activities",
        json={"contactId": "does-not-exist", "type": "Call", "note": "x"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert client.get("/contacts/does-not-exist/activities").status_code == 404


def test_activity_is_not_attached_to_deals(client, auth_headers, make_contact):
    contact = make_contact()
    response = client.post(
        "/activities",
        json={"contactId": contact["id"], "type": "Note", "note": "x", "dealId": "d1"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert "dealId" not in response.json()
