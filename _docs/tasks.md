# Backlog

Tasks derived from `plan.md` (the MVP specification). Each task is scoped to
be completable in one session and handed to someone who has not read the
others — see `_docs/task-template.md` for how each should be groomed before
implementation, and `_docs/process.md` for the PM → Engineer → QA lifecycle.

Backend work should conform to the contract already defined in
`openapi.yaml`. Frontend work should follow the existing design system in
`_frontend/` (see `_frontend/readme.md`).

## 1. Contact data model and validation
Goal: A Contact record enforces the MVP's required fields and its one-company-per-contact rule.
Description: Define the Contact schema (name, email, phone, company, job_title, address, website, tags) and validate it at the data/model boundary, not just in the UI. Company stays a plain field on Contact, never a separate entity or table.

## 2. Contact CRUD API
Goal: Contacts can be created, fetched, and edited through the API.
Description: Implement the create, get, and update contact endpoints per `openapi.yaml` (`POST /contacts`, `GET /contacts/{contactId}`, `PATCH /contacts/{contactId}` or equivalent). Reuse the validation from Task 1 rather than re-implementing it.

## 3. Contact search API
Goal: Contacts can be found by name, email, or company.
Description: Implement the `search` behavior on `GET /contacts` so it matches case-insensitively against name, email, or company as a substring, returning results sorted by name.

## 4. Contact tag filter API
Goal: Contacts can be filtered down to those matching a set of tags.
Description: Implement the `tags` query parameter on `GET /contacts` so it returns only contacts that carry every listed tag. Also implement `GET /tags` so the UI can populate a filter list.

## 5. Deal data model and validation
Goal: A Deal record enforces that it always belongs to exactly one existing contact and always has a current pipeline stage.
Description: Define the Deal schema (contact, pipeline stage) and validate the contact relationship and stage value at the data/model boundary. Reject deals that reference a missing contact or an invalid stage.

## 6. Deal CRUD API
Goal: Deals can be created from a contact, viewed, and edited through the API.
Description: Implement `POST /deals` (creating a deal always associates it with the given contact), `GET /deals/{dealId}`, and the update endpoint per `openapi.yaml`. Reuse the validation from Task 5.

## 7. Manual deal stage movement
Goal: A deal can be moved between pipeline stages, including into Won or Lost, with no side effects.
Description: Implement the stage-change path on the deal update endpoint. Moving to Won or Lost is just setting the stage field — there is no separate action, no reason field, and no automation triggered by the change.

## 8. Pipeline definition API
Goal: The single pipeline's ordered list of stages is available to clients.
Description: Implement `GET /pipeline` returning the one pipeline's stages in display order. If default stage names are needed, use conventional minimal ones (e.g. Lead, Qualified, Proposal, Won, Lost) and do not introduce a way to define multiple pipelines.

## 9. Activity data model and validation
Goal: An Activity record enforces that it always belongs to exactly one existing contact and has a valid type.
Description: Define the Activity schema (type: call/email/meeting/note, plus whatever content fields it needs) and validate the contact relationship and type at the data/model boundary. Activities never reference a deal.

## 10. Activity API
Goal: Activities can be recorded against a contact and listed as that contact's history.
Description: Implement `POST /activities` (always scoped to a contact) and `GET /contacts/{contactId}/activities` per `openapi.yaml`, returning them in an order suitable for a history view (most recent first).

## 11. Contacts list and search UI
Goal: A user can see all contacts and narrow the list by search text.
Description: Build the contacts list view backed by the search API (Task 3), showing name, email, and company per row, using the existing design system components (`.table`, `.field`/`.input`).

## 12. Tag filter UI
Goal: A user can filter the visible contact list by one or more tags.
Description: Add a tag filter control to the contacts list view backed by the tags/filter API (Task 4), using the existing `.tag` components.

## 13. Contact detail view UI
Goal: A user can see all information for a single contact in one place.
Description: Build the contact detail view showing the contact's fields, with clearly separated sections for activity history and associated deals (built out in Tasks 15 and 17).

## 14. Contact create/edit form UI
Goal: A user can create a new contact or edit an existing one, including required company info.
Description: Build a form covering all Contact fields (name, email, phone, company, job_title, address, website, tags) that calls the create/edit API from Task 2, using the existing `.field`/`.input`/`.dialog` components.

## 15. Activity history UI
Goal: A user can see a contact's past interactions and add a new one.
Description: On the contact detail view, list activities from Task 10 in reverse-chronological order, and provide a way to record a new activity by choosing Call, Email, Meeting, or Note.

## 16. Associated deals UI
Goal: A user can see a contact's deals directly from the contact detail view.
Description: On the contact detail view, list the deals belonging to that contact (stage and basic deal info) with a way to open each one, and a way to create a new deal from this contact via the API from Task 6.

## 17. Pipeline board UI
Goal: A user can see all deals grouped by their current pipeline stage.
Description: Build the Deals section's pipeline view backed by the pipeline (Task 8) and deals list APIs, rendering one column per stage with the deals currently in it.

## 18. Move deal between stages UI
Goal: A user can manually move a deal to a different stage from the pipeline board.
Description: Add the interaction (e.g. a stage selector or drag action) that calls the stage-update API from Task 7. No confirmation workflow or automation should be attached to reaching Won or Lost.

## 19. Deal detail and edit UI
Goal: A user can open a single deal, see its contact, and edit it.
Description: Build a deal detail view reachable from the pipeline board that shows the associated contact (with a link back to the contact detail view) and allows editing the deal via the API from Task 6.

## 20. Main navigation shell
Goal: A user can move between the Contacts and Deals sections.
Description: Build the top-level navigation with exactly two entries, Contacts and Deals, using the existing `.nav` component. No other primary sections (e.g. a dashboard) should be added.

## 21. Cross-entity relationship enforcement
Goal: The three core relationships (contact→company field, deal→contact, activity→contact) cannot be violated regardless of which client calls the API.
Description: Add or verify server-side checks that a deal cannot be created or updated to reference a nonexistent contact, an activity cannot be created without a contact, and a contact cannot be saved without a company value. This is a review/hardening pass across Tasks 1, 5, and 9, not new endpoints.

## 22. Local development seed data
Goal: A developer can run the app locally and immediately see representative contacts, deals, and activities.
Description: Add a small, fixed seed dataset (a handful of contacts across a few companies, a few deals across different stages including Won and Lost, and a few activities of each type) usable for local development and manual QA.
