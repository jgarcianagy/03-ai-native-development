# Simple CRM

A lightweight CRM MVP for managing client relationships: contacts, their activity history, and a single-pipeline view of deals.

## Domain model

- **Contact** — a person, belonging to exactly one company (a field, not a separate entity).
- **Activity** — a call, email, meeting, or note logged against a contact.
- **Deal** — a sales opportunity tied to one contact, moved manually through pipeline stages (including Won/Lost).

There is one pipeline, no automation, and no separate company entity — see [CLAUDE.md](CLAUDE.md) for the full scope.

## Stack

- **Backend**: FastAPI + SQLAlchemy (`backend/`)
- **Frontend**: static HTML/CSS/JS (`_frontend/`)

## Running locally

```bash
make run            # backend API on :8091
make run-frontend    # frontend on :8092
make test            # backend test suite
```

## Interface

![Simple CRM interface](interface.png)

Contact detail view showing profile info, associated deals, and activity history/logging.
