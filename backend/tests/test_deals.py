def test_list_deals_returns_seeded_data_enriched_with_contact_info(client):
    response = client.get("/api/deals")
    assert response.status_code == 200
    deals = response.json()
    assert len(deals) >= 6
    for deal in deals:
        assert deal["contactName"]
        assert deal["company"]


def test_filter_deals_by_contact(client):
    contacts = client.get("/api/contacts").json()
    ava = next(c for c in contacts if c["name"] == "Ava Thompson")
    response = client.get("/api/deals", params={"contactId": ava["id"]})
    assert response.status_code == 200
    deals = response.json()
    assert len(deals) == 2
    assert all(d["contactId"] == ava["id"] for d in deals)


def test_filter_deals_by_stage(client):
    response = client.get("/api/deals", params={"stage": "Won"})
    assert response.status_code == 200
    deals = response.json()
    assert len(deals) == 1
    assert deals[0]["stage"] == "Won"


def test_get_deal_by_id(client):
    deals = client.get("/api/deals").json()
    deal_id = deals[0]["id"]
    response = client.get(f"/api/deals/{deal_id}")
    assert response.status_code == 200
    assert response.json()["id"] == deal_id


def test_get_missing_deal_returns_404(client):
    response = client.get("/api/deals/does-not-exist")
    assert response.status_code == 404


def test_create_deal_requires_auth(client):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/deals", json={"contactId": contacts[0]["id"], "title": "New Deal"}
    )
    assert response.status_code == 401


def test_create_deal_requires_contact_and_title(client, auth_headers):
    response = client.post("/api/deals", json={"title": "No contact"}, headers=auth_headers)
    assert response.status_code == 400
    assert "contact" in response.json()["error"].lower()

    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/deals", json={"contactId": contacts[0]["id"]}, headers=auth_headers
    )
    assert response.status_code == 400
    assert "title" in response.json()["error"].lower()


def test_create_deal_rejects_unknown_contact(client, auth_headers):
    response = client.post(
        "/api/deals",
        json={"contactId": "does-not-exist", "title": "Deal"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_deal_defaults_stage_to_lead(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/deals",
        json={"contactId": contacts[0]["id"], "title": "Unstaged deal"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["stage"] == "Lead"


def test_create_deal_rejects_unknown_stage(client, auth_headers):
    contacts = client.get("/api/contacts").json()
    response = client.post(
        "/api/deals",
        json={"contactId": contacts[0]["id"], "title": "Deal", "stage": "Bogus"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_move_deal_between_stages(client, auth_headers):
    deals = client.get("/api/deals", params={"stage": "Lead"}).json()
    deal_id = deals[0]["id"]
    response = client.patch(
        f"/api/deals/{deal_id}", json={"stage": "Qualified"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["stage"] == "Qualified"


def test_move_deal_to_won(client, auth_headers):
    deals = client.get("/api/deals", params={"stage": "Lead"}).json()
    deal_id = deals[0]["id"]
    response = client.patch(f"/api/deals/{deal_id}", json={"stage": "Won"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["stage"] == "Won"


def test_update_deal_requires_auth(client):
    deals = client.get("/api/deals").json()
    response = client.patch(f"/api/deals/{deals[0]['id']}", json={"stage": "Won"})
    assert response.status_code == 401


def test_update_missing_deal_returns_404(client, auth_headers):
    response = client.patch(
        "/api/deals/does-not-exist", json={"stage": "Won"}, headers=auth_headers
    )
    assert response.status_code == 404
