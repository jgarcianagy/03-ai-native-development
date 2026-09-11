def test_list_contacts_returns_seeded_data_sorted_by_name(client):
    response = client.get("/api/contacts")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == sorted(names, key=str.lower)
    assert len(names) >= 5


def test_search_matches_name_email_or_company(client):
    response = client.get("/api/contacts", params={"search": "Northfield"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["company"] == "Northfield Industries"


def test_search_is_case_insensitive(client):
    response = client.get("/api/contacts", params={"search": "priya"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_by_tags_requires_all_listed_tags(client):
    response = client.get("/api/contacts", params={"tags": "vip"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all("vip" in c["tags"] for c in body)


def test_filter_by_multiple_tags(client):
    response = client.get("/api/contacts", params={"tags": "vip,decision-maker"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Priya Natarajan"


def test_get_contact_by_id(client):
    listed = client.get("/api/contacts").json()
    contact_id = listed[0]["id"]
    response = client.get(f"/api/contacts/{contact_id}")
    assert response.status_code == 200
    assert response.json()["id"] == contact_id


def test_get_missing_contact_returns_404_with_error_body(client):
    response = client.get("/api/contacts/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()


def test_create_contact_requires_name_and_company(client, auth_headers):
    response = client.post(
        "/api/contacts", json={"company": "Acme"}, headers=auth_headers
    )
    assert response.status_code == 400
    assert "name" in response.json()["error"].lower()

    response = client.post(
        "/api/contacts", json={"name": "No Company"}, headers=auth_headers
    )
    assert response.status_code == 400
    assert "company" in response.json()["error"].lower()


def test_create_contact_accepts_comma_separated_tags_string(client, auth_headers):
    response = client.post(
        "/api/contacts",
        json={"name": "Tag Test", "company": "Acme", "tags": "a, b ,c"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["a", "b", "c"]


def test_update_contact_changes_only_supplied_fields(client, auth_headers):
    created = client.post(
        "/api/contacts",
        json={"name": "Original Name", "company": "Original Co", "phone": "111"},
        headers=auth_headers,
    ).json()

    response = client.patch(
        f"/api/contacts/{created['id']}",
        json={"phone": "222"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Original Name"
    assert body["phone"] == "222"


def test_update_contact_rejects_blank_name(client, auth_headers):
    listed = client.get("/api/contacts").json()
    contact_id = listed[0]["id"]
    response = client.patch(
        f"/api/contacts/{contact_id}", json={"name": "  "}, headers=auth_headers
    )
    assert response.status_code == 400


def test_update_contact_requires_auth(client):
    listed = client.get("/api/contacts").json()
    contact_id = listed[0]["id"]
    response = client.patch(f"/api/contacts/{contact_id}", json={"phone": "999"})
    assert response.status_code == 401


def test_list_tags_returns_sorted_distinct_tags(client):
    response = client.get("/api/tags")
    assert response.status_code == 200
    tags = response.json()
    assert tags == sorted(tags)
    assert len(tags) == len(set(tags))


def test_list_activities_for_contact(client):
    listed = client.get("/api/contacts").json()
    ava = next(c for c in listed if c["name"] == "Ava Thompson")
    response = client.get(f"/api/contacts/{ava['id']}/activities")
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) == 2
    assert all(a["contactId"] == ava["id"] for a in activities)
    # newest first
    assert activities[0]["at"] >= activities[1]["at"]


def test_list_activities_for_missing_contact_returns_404(client):
    response = client.get("/api/contacts/does-not-exist/activities")
    assert response.status_code == 404
