# Deploying to Google Cloud

The app ships as a single container (see `Dockerfile`): FastAPI serves both
the API (`/api`) and the built frontend (`/`). On GCP it runs as:

| Piece         | GCP service               | Notes                                                  |
|---------------|---------------------------|--------------------------------------------------------|
| App           | Cloud Run                 | Scales to zero, max 2 instances, private behind IAP    |
| Access        | Identity-Aware Proxy      | Google sign-in; only `CRM_IAP_MEMBERS` get in          |
| Database      | Cloud SQL, Postgres 16    | `db-f1-micro`, daily backups, point-in-time recovery, deletion protection |
| DB password   | Secret Manager            | Full URL stored as secret `crm-database-url`           |
| Images        | Artifact Registry         | Pushed by CI (or built by Cloud Build for manual deploys) |

All of it is scripted in `deploy/gcp.sh`.

## Prerequisites

- A GCP project with billing enabled. IAP works most simply when the project
  belongs to a Google Workspace / Cloud Identity organization and the users
  are in it; see [Known limitations](#known-limitations) otherwise.
- [`gcloud` CLI](https://cloud.google.com/sdk/docs/install), logged in as a
  project owner: `gcloud auth login`
- `openssl` (generates the DB password) and `jq` (used by `gcp.sh verify`).
  Docker is **not** needed for manual deploys; Cloud Build builds the image.

## First deploy

```sh
export GCP_PROJECT=your-project-id
export GCP_REGION=europe-west1   # optional, this is the default

# One-time: APIs, Cloud SQL, secret, service account, IAP access (~10 min).
# CRM_IAP_MEMBERS: who may open the app (comma-separated IAM members).
CRM_IAP_MEMBERS="user:you@example.com,group:sales@example.com" make gcp-setup

make gcp-deploy   # build + release + verify; prints the URL
```

Open the URL and sign in with a Google account listed in `CRM_IAP_MEMBERS`.
To grant access later, re-run `make gcp-setup` with the new list (it only
adds members), or grant `roles/iap.httpsResourceAccessor` in the console.

## Updating

Normally CI deploys (below). For a manual deploy, commit your changes and run
`make gcp-deploy`; images are tagged with the git short SHA.

### Database schema

The schema is managed with Alembic (`backend/app/migrations/`). The app runs
pending migrations on startup, holding a Postgres advisory lock so several
instances starting at once don't race. To change the schema, edit
`backend/app/db_models.py`, then generate and review a migration:

```sh
cd backend
SDIP_DATABASE_URL=sqlite:///./crm.db uv run --with-requirements requirements-dev.txt \
  alembic revision --autogenerate -m "describe the change"
```

`backend/tests/test_schema.py` fails if the migrations and the models drift
apart. Keep migrations backward compatible with the previous release (e.g.
add a column as nullable first): the old revision keeps serving until the new
one passes its startup probe.

Production starts with an **empty** database: demo data is only seeded when
`SDIP_SEED_DEMO_DATA` isn't `false`, and `gcp.sh release` sets it to `false`.

## CI/CD (GitHub Actions)

`.github/workflows/ci-cd.yml` runs on every pull request and push to `main`:

1. **Backend tests** (`make test`), **frontend tests** (plus the production
   build) and a **dependency audit** (`pip-audit` on the pinned
   `backend/requirements.txt`), in parallel.
2. **Integration + E2E**: builds the Docker Compose stack, runs
   `integration_tests/` against it, then the Playwright browser tests in
   `e2e_tests/` against the same stack. Stack logs and Playwright traces are
   kept when a step fails. On `main`, the image that passed is saved as a
   build artifact.
3. **Deploy** (pushes to `main` only, **skipped until the `GCP_PROJECT`
   repository variable exists**, and waiting for approval on the `production`
   environment):
   - authenticates to GCP with GitHub's OIDC token (no stored key);
   - pushes **the exact image the tests ran against** (`gcp.sh push` with
     `CRM_LOCAL_IMAGE`), tagged with the commit SHA;
   - releases it (`gcp.sh release`). Cloud Run's startup probe calls
     `/api/health`, which only passes once the database is reachable; a
     revision that never passes gets no traffic, so **the previous revision
     keeps serving** and the job fails;
   - verifies through the Cloud Run API (`gcp.sh verify`) that the ready
     revision runs this image and gets 100% of traffic. (IAP blocks anonymous
     HTTP, so CI doesn't call the URL directly.)

All steps run in bash with `pipefail`, and third-party actions are pinned to
commit SHAs; `.github/dependabot.yml` opens weekly update PRs for actions,
Python dependencies and base images.

### Repository settings

- **`main` is protected**: changes go through a pull request, and the backend,
  frontend, dependency-audit and integration/E2E checks must pass. Force
  pushes and deleting `main` are blocked.
- **`production` environment**: requires a reviewer's approval before the
  deploy job runs, and only accepts deployments from `main`.

### One-time setup

After `make gcp-setup`:

```sh
GITHUB_REPO=owner/name make gcp-setup-ci
```

This creates a Workload Identity pool + GitHub OIDC provider that only accepts
tokens from jobs in that repository's `main` branch using the `production`
environment, and a `crm-deployer` service account the workflow impersonates
(roles: `run.admin` and `iap.admin`, which Google requires for deploying
IAP-protected services; `artifactregistry.writer` on the `crm` repository;
`iam.serviceAccountUser` on `crm-runner`). No service account key is created.
It prints four `gh variable set` commands: run them to set `GCP_PROJECT`,
`GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER` and
`GCP_DEPLOY_SERVICE_ACCOUNT`. Setting `GCP_PROJECT` is what turns on the
deploy job.

## Configuration

`deploy/gcp.sh`:

| Variable               | Default        | Purpose                                         |
|------------------------|----------------|-------------------------------------------------|
| `GCP_PROJECT`          | (required)     | Project ID                                      |
| `GCP_REGION`           | `europe-west1` | Region for all resources                        |
| `CRM_IAP_MEMBERS`      | (required for `setup`) | Who may open the app, e.g. `user:a@x.com,domain:x.com` |
| `CRM_SERVICE`          | `simple-crm`   | Cloud Run service name                          |
| `CRM_SQL_INSTANCE`     | `crm-db`       | Cloud SQL instance name                         |
| `CRM_SQL_TIER`         | `db-f1-micro`  | Cloud SQL machine tier                          |
| `CRM_SQL_AVAILABILITY` | `zonal`        | `regional` for high availability (about 2x cost) |
| `CRM_MAX_INSTANCES`    | `2`            | Cloud Run max instances (mind DB connections)   |
| `CRM_LOCAL_IMAGE`      | (unset)        | `push`: push this local image instead of building |

The container reads:

| Variable                | Default (image)          | Purpose                                              |
|-------------------------|--------------------------|------------------------------------------------------|
| `SDIP_DATABASE_URL`     | SQLite in `/data`        | Database (injected from Secret Manager on GCP)       |
| `SDIP_SEED_DEMO_DATA`   | `true`                   | Seed demo data into an empty database (`false` on GCP) |
| `SDIP_CORS_ORIGINS`     | empty (CORS off)         | Comma-separated allowed origins; `*` in local dev    |
| `SDIP_TOKEN_TTL_HOURS`  | `12`                     | Login token lifetime                                 |
| `SDIP_DB_POOL_SIZE` / `SDIP_DB_MAX_OVERFLOW` | `5` / `2` | Postgres connections per instance            |
| `APP_VERSION`           | `dev`                    | Image tag, reported by `/api/health`                 |
| `PORT`                  | `8000`                   | Set by Cloud Run                                     |

## Known limitations

- **IAP is the access control.** The frontend still logs in to the API with
  the built-in `admin` / `admin123` user (`_frontend/crm-service.js`), so
  everyone let through by IAP has full read/write access, and there are no
  per-user accounts or audit trail. That matches the MVP scope; per-user
  accounts would be a separate product decision.
- **Users outside your organization**: for a project without an organization,
  or to admit external Google accounts, IAP needs an OAuth consent screen and
  extra roles (`roles/iap.settingsAdmin`, `roles/oauthconfig.editor`); see
  [IAP for Cloud Run](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run).
- **Small database tier.** `db-f1-micro` is shared-core and has no SLA. For
  real use, consider `CRM_SQL_TIER=db-g1-small` or larger (set before
  `make gcp-setup`, or change the tier in the console), and raise
  `CRM_MAX_INSTANCES` only as far as the tier's connection limit allows.
- **Cold starts.** `--min-instances 0` keeps cost near zero but the first
  request after idle takes a few seconds.

## Troubleshooting

- **`gcloud builds submit` fails with a permission error**: on newer projects
  Cloud Build runs as the Compute Engine default service account, which may lack
  roles. Grant it `roles/artifactregistry.writer` and `roles/logging.logWriter`.
- **Deploy fails with "revision is not ready"**: the startup probe on
  `/api/health` never passed, usually because the database is unreachable or a
  migration failed. The previous revision is still serving. Check logs with
  `gcloud run services logs read simple-crm --region $GCP_REGION`.
- **"You don't have access" after signing in**: the account isn't in
  `CRM_IAP_MEMBERS`; re-run `make gcp-setup` with it added.
- **Rotate the DB password**: delete the `crm-database-url` secret and re-run
  `make gcp-setup` (it resets the password and recreates the secret), then
  `make gcp-deploy`.
- **Delete the database**: deletion protection must be turned off first
  (`gcloud sql instances patch crm-db --no-deletion-protection`).
