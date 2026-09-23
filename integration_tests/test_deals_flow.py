"""Create a deal from a contact and move it manually through the pipeline."""
import pytest

STAGES = ["Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]


@pytest.fixture
def make_deal(client, auth_headers, make_contact):
    def _make(**overrides) -> dict:
        contact = overrides.pop("contact", None) or make_contact()
        payload = {"contactId": contact["id"], "title": "Integration deal", **overrides}
        response = client.post("/deals", json=payload, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


def test_new_deal_defaults_to_lead_and_is_enriched_with_contact(make_deal, make_contact):
    contact = make_contact()
    deal = make_deal(contact=contact, value=1234.5, expectedClose="2026-12-31")
    assert deal["stage"] == "Lead"
    assert deal["contactId"] == contact["id"]
    assert deal["contactName"] == contact["name"]
    assert deal["company"] == contact["company"]
    assert deal["value"] == 1234.5
    assert deal["expectedClose"] == "2026-12-31"


def test_deal_appears_in_pipeline_and_on_contact(client, make_deal, make_contact):
    contact = make_contact()
    deal = make_deal(contact=contact)

    assert deal["id"] in [d["id"] for d in client.get("/deals", params={"stage": "Lead"}).json()]
    assert [d["id"] for d in client.get("/deals", params={"contactId": contact["id"]}).json()] == [deal["id"]]


def test_move_deal_through_every_stage_is_persisted(client, auth_headers, make_deal):
    deal = make_deal()
    for stage in STAGES[1:]:
        response = client.patch(f"/deals/{deal['id']}", json={"stage": stage}, headers=auth_headers)
        assert response.status_code == 200
        assert client.get(f"/deals/{deal['id']}").json()["stage"] == stage

    # Won/Lost are ordinary stages: a deal can be moved back out of them.
    response = client.patch(f"/deals/{deal['id']}", json={"stage": "Qualified"}, headers=auth_headers)
    assert response.status_code == 200


def test_stage_move_triggers_no_automation(client, auth_headers, make_deal, make_contact):
    contact = make_contact()
    deal = make_deal(contact=contact, value=500, expectedClose="2026-10-10")

    client.patch(f"/deals/{deal['id']}", json={"stage": "Won"}, headers=auth_headers).raise_for_status()

    after = client.get(f"/deals/{deal['id']}").json()
    assert {**deal, "stage": "Won"} == after
    assert client.get(f"/contacts/{contact['id']}/activities").json() == []
    assert len(client.get("/deals", params={"contactId": contact["id"]}).json()) == 1


def test_deal_must_belong_to_an_existing_contact(client, auth_headers, make_deal):
    response = client.post("/deals", json={"title": "Orphan"}, headers=auth_headers)
    assert response.status_code == 400

    response = client.post("/deals", json={"title": "Orphan", "contactId": "nope"}, headers=auth_headers)
    assert response.status_code == 400

    deal = make_deal()
    response = client.patch(f"/deals/{deal['id']}", json={"contactId": "nope"}, headers=auth_headers)
    assert response.status_code == 400


def test_unknown_stage_is_rejected_and_not_persisted(client, auth_headers, make_deal):
    deal = make_deal()
    response = client.patch(f"/deals/{deal['id']}", json={"stage": "Archived"}, headers=auth_headers)
    assert response.status_code == 400
    assert client.get(f"/deals/{deal['id']}").json()["stage"] == "Lead"


def test_editing_contact_is_reflected_on_its_deals(client, auth_headers, make_deal, make_contact, unique):
    contact = make_contact()
    deal = make_deal(contact=contact)
    client.patch(
        f"/contacts/{contact['id']}", json={"company": f"Renamed {unique}"}, headers=auth_headers
    ).raise_for_status()

    assert client.get(f"/deals/{deal['id']}").json()["company"] == f"Renamed {unique}"
