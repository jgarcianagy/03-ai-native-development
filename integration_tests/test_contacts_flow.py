"""Create / view / edit / find a contact, end to end through Postgres."""


def test_create_view_and_edit_contact(client, auth_headers, make_contact, unique):
    created = make_contact(phone="+1-555-9999", jobTitle="Buyer", tags="alpha, beta")
    assert created["tags"] == ["alpha", "beta"]

    fetched = client.get(f"/contacts/{created['id']}").json()
    assert fetched == created

    response = client.patch(
        f"/contacts/{created['id']}",
        json={"jobTitle": "Head of Buying", "tags": ["alpha"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    updated = client.get(f"/contacts/{created['id']}").json()
    assert updated["jobTitle"] == "Head of Buying"
    assert updated["tags"] == ["alpha"]
    # Fields not in the patch are untouched.
    assert updated["name"] == created["name"]
    assert updated["phone"] == "+1-555-9999"


def test_contact_requires_name_and_company(client, auth_headers):
    response = client.post("/contacts", json={"name": "No Company"}, headers=auth_headers)
    assert response.status_code == 400
    assert "company" in response.json()["error"].lower()

    response = client.post("/contacts", json={"company": "No Name Inc"}, headers=auth_headers)
    assert response.status_code == 400


def test_edit_cannot_blank_out_company(client, auth_headers, make_contact):
    contact = make_contact()
    response = client.patch(f"/contacts/{contact['id']}", json={"company": "  "}, headers=auth_headers)
    assert response.status_code == 400
    assert client.get(f"/contacts/{contact['id']}").json()["company"] == contact["company"]


def test_search_by_name_email_and_company_is_case_insensitive(client, make_contact, unique):
    contact = make_contact(
        name=f"Zelda Quux {unique}",
        email=f"zq.{unique}@quuxmail.test",
        company=f"Quux Holdings {unique}",
    )

    for term in (f"zelda quux {unique}", f"ZQ.{unique}@", f"quux holdings {unique}"):
        ids = [c["id"] for c in client.get("/contacts", params={"search": term}).json()]
        assert ids == [contact["id"]], term


def test_filter_by_tags_requires_all_tags(client, make_contact, unique):
    both = make_contact(name=f"Both {unique}", tags=[f"t1-{unique}", f"t2-{unique}"])
    make_contact(name=f"One {unique}", tags=[f"t1-{unique}"])

    one_tag = client.get("/contacts", params={"tags": f"t1-{unique}"}).json()
    assert len(one_tag) == 2

    two_tags = client.get("/contacts", params={"tags": f"t1-{unique},t2-{unique}"}).json()
    assert [c["id"] for c in two_tags] == [both["id"]]

    assert f"t2-{unique}" in client.get("/tags").json()


def test_search_and_tag_filter_combine(client, make_contact, unique):
    target = make_contact(name=f"Combo Target {unique}", tags=[f"combo-{unique}"])
    make_contact(name=f"Combo Other {unique}", tags=[])

    result = client.get("/contacts", params={"search": f"combo", "tags": f"combo-{unique}"}).json()
    assert [c["id"] for c in result] == [target["id"]]


def test_missing_contact_returns_404(client):
    assert client.get("/contacts/does-not-exist").status_code == 404
