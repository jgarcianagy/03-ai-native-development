# Simple CRM

A lightweight CRM MVP for managing client relationships: contacts, their activity history, and a single-pipeline view of deals.

## Domain model

- **Contact** — a person, belonging to exactly one company (a field, not a separate entity).
- **Activity** — a call, email, meeting, or note logged against a contact.
- **Deal** — a sales opportunity tied to one contact, moved manually through pipeline stages (including Won/Lost).

There is one pipeline, no automation, and no separate company entity — see [CLAUDE.md](CLAUDE.md) for the full scope.

## Stack

- **Backend**: FastAPI + SQLAlchemy, Alembic migrations run on startup (`backend/`)
- **Database**: SQLite locally, Postgres 16 in Docker Compose and production
- **Frontend**: static HTML/CSS/JS (`_frontend/`), served by the backend in the container image
- **API contract**: [openapi.yaml](openapi.yaml)

## Running locally

```bash
make run            # backend API on :8091 (SQLite, ./backend/crm.db)
make run-frontend    # frontend on :8092
```

Or run the production-shaped stack (single app container + Postgres):

```bash
docker compose up --build   # app on http://localhost:8001
```

## Tests

```bash
make test              # backend unit tests
make test-frontend     # frontend services-layer tests (Node)
make test-integration  # API tests against an isolated Docker Compose stack
make test-e2e          # Playwright browser tests against the same stack
```

## Configuration

| Variable               | Default               | Purpose                                            |
|------------------------|-----------------------|----------------------------------------------------|
| `SDIP_DATABASE_URL`    | `sqlite:///./crm.db`  | SQLAlchemy database URL                            |
| `SDIP_CORS_ORIGINS`    | `*`                   | Comma-separated allowed origins; empty disables CORS (as in the image) |
| `SDIP_SEED_DEMO_DATA`  | `true`                | Seed demo contacts/deals; `false` in production    |
| `SDIP_TOKEN_TTL_HOURS` | `12`                  | Login token lifetime                               |
| `SDIP_DB_POOL_SIZE` / `SDIP_DB_MAX_OVERFLOW` | `5` / `2` | Postgres connection pool sizing          |

## Deployment

Production runs on Google Cloud: Cloud Run (private behind Identity-Aware
Proxy) with Cloud SQL Postgres, scripted in `deploy/gcp.sh`:

```bash
export GCP_PROJECT=your-project-id
CRM_IAP_MEMBERS="user:you@example.com" make gcp-setup   # one-time infrastructure
make gcp-deploy                                         # build, release, verify
```

CI/CD (GitHub Actions) runs all test suites plus a `pip-audit` check and, once
the `GCP_PROJECT` repo variable is set and a reviewer approves, deploys the
tested image from `main`. See [_docs/deploy-gcp.md](_docs/deploy-gcp.md) for
setup, schema migrations, and CI details.

## Interface

![Simple CRM interface](interface.png)

Contact detail view showing profile info, associated deals, and activity history/logging.
