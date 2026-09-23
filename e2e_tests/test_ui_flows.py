"""The MVP user flows from CLAUDE.md, driven through the browser."""
import re

from playwright.sync_api import expect


def test_create_a_contact_and_find_it_again(page, app_url, api, unique):
    name, company = f"Ines Ortega {unique}", f"Ortega Studio {unique}"
    page.goto(app_url)

    page.get_by_role("button", name="New", exact=True).click()
    dialog = page.locator(".dialog")
    dialog.locator('input[name="name"]').fill(name)
    dialog.locator('input[name="company"]').fill(company)
    dialog.locator('input[name="email"]').fill(f"ines.{unique}@example.com")
    dialog.locator('input[name="tags"]').fill(f"e2e-{unique}")
    dialog.get_by_role("button", name="Create").click()

    expect(dialog).to_have_count(0)
    expect(page.get_by_role("heading", level=2, name=name)).to_be_visible()

    # Persisted: a fresh page load finds it by company, then by tag filter.
    page.reload()
    page.get_by_label("Search contacts").fill(company)
    expect(page.get_by_role("button", name=re.compile(name))).to_have_count(1)
    page.get_by_label("Search contacts").fill("")
    page.get_by_role("button", name=f"e2e-{unique}", exact=True).click()
    expect(page.locator("button.crm-row")).to_have_count(1)
    expect(page.locator("button.crm-row")).to_contain_text(name)

    assert [c["name"] for c in api.get("/contacts", params={"search": company}).json()] == [name]


def test_record_an_interaction(page, api, contact, open_contact, unique):
    note = f"Discussed renewal {unique}"
    open_contact(contact)

    page.get_by_role("button", name="Meeting", exact=True).click()
    page.get_by_placeholder("What happened?").fill(note)
    page.get_by_role("button", name="Log activity").click()

    # The composer clears once saved, and the entry shows in the history.
    expect(page.get_by_placeholder("What happened?")).to_have_value("")
    expect(page.get_by_text(note, exact=True)).to_be_visible()
    activities = api.get(f"/contacts/{contact['id']}/activities").json()
    assert [(a["type"], a["note"]) for a in activities] == [("Meeting", note)]


def test_create_a_deal_and_move_it_through_the_pipeline(page, api, contact, open_contact, unique):
    title = f"Website rebuild {unique}"
    open_contact(contact)

    page.get_by_role("button", name="New deal").click()
    dialog = page.locator(".dialog")
    dialog.locator('input[name="title"]').fill(title)
    dialog.locator('input[name="value"]').fill("4200")
    dialog.locator('input[name="expectedClose"]').fill("2026-12-31")
    dialog.get_by_role("button", name="Create").click()
    expect(dialog).to_have_count(0)

    [deal] = api.get("/deals", params={"contactId": contact["id"]}).json()
    assert (deal["title"], deal["stage"]) == (title, "Lead")

    # Open it from the pipeline and move it manually to Won.
    page.get_by_role("button", name="Deals", exact=True).click()
    page.get_by_text(title).click()
    dialog.locator('select[name="stage"]').select_option("Won")
    dialog.get_by_role("button", name="Save").click()
    expect(dialog).to_have_count(0)

    assert api.get(f"/deals/{deal['id']}").json()["stage"] == "Won"
    # The card is still reachable and links back to its contact.
    page.get_by_role("button", name=contact["name"]).click()
    expect(page.get_by_role("heading", level=2, name=contact["name"])).to_be_visible()
