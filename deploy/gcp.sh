#!/usr/bin/env bash
# Deploys the CRM to Google Cloud: Cloud Run (app) + Cloud SQL Postgres (data).
#
#   GCP_PROJECT=my-project CRM_IAP_MEMBERS=user:you@example.com ./deploy/gcp.sh setup   # one-time
#   GCP_PROJECT=my-project ./deploy/gcp.sh deploy   # build (Cloud Build) + release + verify
#
# For GitHub Actions (see .github/workflows/ci-cd.yml):
#   GCP_PROJECT=my-project GITHUB_REPO=owner/name ./deploy/gcp.sh setup-ci   # one-time
#   ./deploy/gcp.sh push      # push an image to Artifact Registry (CRM_LOCAL_IMAGE, or build one)
#   ./deploy/gcp.sh release   # deploy the pushed image to Cloud Run
#   ./deploy/gcp.sh verify    # check the new revision is ready and serving all traffic
#
# All commands are safe to re-run; setup steps skip resources that already exist.
# See _docs/deploy-gcp.md for details.
set -euo pipefail

PROJECT="${GCP_PROJECT:?Set GCP_PROJECT to your Google Cloud project ID}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE="${CRM_SERVICE:-simple-crm}"
SQL_INSTANCE="${CRM_SQL_INSTANCE:-crm-db}"
SQL_TIER="${CRM_SQL_TIER:-db-f1-micro}"
SQL_AVAILABILITY="${CRM_SQL_AVAILABILITY:-zonal}" # "regional" = high availability (about 2x cost)
# Each instance opens up to 7 database connections (backend/app/database.py);
# db-f1-micro allows 25, so keep MAX_INSTANCES x 7 below that on small tiers.
MAX_INSTANCES="${CRM_MAX_INSTANCES:-2}"
DB_NAME=crm
DB_USER=crm
REPO=crm
DB_URL_SECRET=crm-database-url
RUNTIME_SA="crm-runner@${PROJECT}.iam.gserviceaccount.com"
DEPLOY_SA="crm-deployer@${PROJECT}.iam.gserviceaccount.com"
CONNECTION_NAME="${PROJECT}:${REGION}:${SQL_INSTANCE}"
WIF_POOL=github
WIF_PROVIDER=github-oidc
TAG="${CRM_IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:${TAG}"

gc() { gcloud --project "$PROJECT" --quiet "$@"; }

setup() {
  # Comma-separated IAM members allowed to open the app, e.g.
  # "user:ana@example.com,group:sales@example.com,domain:example.com".
  local IAP_MEMBERS="${CRM_IAP_MEMBERS:?Set CRM_IAP_MEMBERS to who may use the app, e.g. user:you@example.com}"

  echo "==> Enabling APIs"
  gc services enable run.googleapis.com sqladmin.googleapis.com \
    artifactregistry.googleapis.com cloudbuild.googleapis.com \
    secretmanager.googleapis.com iam.googleapis.com iap.googleapis.com

  echo "==> Artifact Registry repository '$REPO'"
  gc artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 ||
    gc artifacts repositories create "$REPO" --repository-format docker --location "$REGION"

  echo "==> Cloud SQL instance '$SQL_INSTANCE' (takes several minutes the first time)"
  gc sql instances describe "$SQL_INSTANCE" >/dev/null 2>&1 ||
    gc sql instances create "$SQL_INSTANCE" --database-version POSTGRES_16 \
      --edition ENTERPRISE --tier "$SQL_TIER" --region "$REGION" \
      --availability-type "$SQL_AVAILABILITY" \
      --storage-auto-increase --backup-start-time 03:00 \
      --enable-point-in-time-recovery --deletion-protection

  gc sql databases describe "$DB_NAME" --instance "$SQL_INSTANCE" >/dev/null 2>&1 ||
    gc sql databases create "$DB_NAME" --instance "$SQL_INSTANCE"

  echo "==> Database user + connection-string secret"
  if ! gc secrets describe "$DB_URL_SECRET" >/dev/null 2>&1; then
    local password
    password="$(openssl rand -hex 24)"
    if gc sql users list --instance "$SQL_INSTANCE" --format 'value(name)' | grep -qx "$DB_USER"; then
      gc sql users set-password "$DB_USER" --instance "$SQL_INSTANCE" --password "$password"
    else
      gc sql users create "$DB_USER" --instance "$SQL_INSTANCE" --password "$password"
    fi
    # Cloud Run mounts the instance as a unix socket under /cloudsql/.
    printf 'postgresql+psycopg2://%s:%s@/%s?host=/cloudsql/%s' \
      "$DB_USER" "$password" "$DB_NAME" "$CONNECTION_NAME" |
      gc secrets create "$DB_URL_SECRET" --data-file -
  fi

  echo "==> Runtime service account"
  gc iam service-accounts describe "$RUNTIME_SA" >/dev/null 2>&1 ||
    gc iam service-accounts create crm-runner --display-name "Simple CRM (Cloud Run)"
  gc projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$RUNTIME_SA" --role roles/cloudsql.client --condition None >/dev/null
  gc secrets add-iam-policy-binding "$DB_URL_SECRET" \
    --member "serviceAccount:$RUNTIME_SA" --role roles/secretmanager.secretAccessor >/dev/null

  # The app is private: Cloud Run only accepts requests from Identity-Aware
  # Proxy, and IAP only lets CRM_IAP_MEMBERS through (Google sign-in).
  echo "==> Identity-Aware Proxy access"
  local project_number iap_agent member
  project_number="$(gc projects describe "$PROJECT" --format 'value(projectNumber)')"
  iap_agent="service-${project_number}@gcp-sa-iap.iam.gserviceaccount.com"
  gc beta services identity create --service iap.googleapis.com >/dev/null
  gc projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$iap_agent" --role roles/run.invoker --condition None >/dev/null
  IFS=',' read -ra members <<<"$IAP_MEMBERS"
  for member in "${members[@]}"; do
    echo "    granting access to $member"
    gc projects add-iam-policy-binding "$PROJECT" \
      --member "$member" --role roles/iap.httpsResourceAccessor --condition None >/dev/null
  done

  echo "Setup complete. Next: GCP_PROJECT=$PROJECT ./deploy/gcp.sh deploy"
}

# Lets GitHub Actions deploy without a stored key: the workflow's OIDC token is
# exchanged (Workload Identity Federation) for the crm-deployer service account,
# and only tokens from jobs in GITHUB_REPO's main branch that use the
# `production` environment (whose reviewers gate deploys) are accepted.
# Run after `setup`.
setup_ci() {
  local github_repo="${GITHUB_REPO:?Set GITHUB_REPO to the GitHub repository, e.g. owner/name}"
  local project_number pool_id
  project_number="$(gc projects describe "$PROJECT" --format 'value(projectNumber)')"
  pool_id="projects/${project_number}/locations/global/workloadIdentityPools/${WIF_POOL}"

  echo "==> Enabling APIs"
  gc services enable iamcredentials.googleapis.com sts.googleapis.com

  echo "==> Workload identity pool '$WIF_POOL' + GitHub OIDC provider"
  gc iam workload-identity-pools describe "$WIF_POOL" --location global >/dev/null 2>&1 ||
    gc iam workload-identity-pools create "$WIF_POOL" --location global --display-name "GitHub Actions"
  local condition="assertion.repository == '${github_repo}' && assertion.ref == 'refs/heads/main' && assertion.environment == 'production'"
  if gc iam workload-identity-pools providers describe "$WIF_PROVIDER" \
    --location global --workload-identity-pool "$WIF_POOL" >/dev/null 2>&1; then
    gc iam workload-identity-pools providers update-oidc "$WIF_PROVIDER" \
      --location global --workload-identity-pool "$WIF_POOL" --attribute-condition "$condition"
  else
    gc iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
      --location global --workload-identity-pool "$WIF_POOL" \
      --display-name "GitHub OIDC" \
      --issuer-uri https://token.actions.githubusercontent.com \
      --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
      --attribute-condition "$condition"
  fi

  echo "==> Deployer service account"
  gc iam service-accounts describe "$DEPLOY_SA" >/dev/null 2>&1 ||
    gc iam service-accounts create crm-deployer --display-name "Simple CRM (GitHub Actions deploy)"
  gc iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
    --member "principalSet://iam.googleapis.com/${pool_id}/attribute.repository/${github_repo}" \
    --role roles/iam.workloadIdentityUser >/dev/null
  # run.admin (not run.developer) and iap.admin are what Google documents for
  # deploying with --iap/--no-allow-unauthenticated, which manage the service's
  # access policy; serviceAccountUser lets it run the service as crm-runner.
  gc projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$DEPLOY_SA" --role roles/run.admin --condition None >/dev/null
  gc projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$DEPLOY_SA" --role roles/iap.admin --condition None >/dev/null
  gc artifacts repositories add-iam-policy-binding "$REPO" --location "$REGION" \
    --member "serviceAccount:$DEPLOY_SA" --role roles/artifactregistry.writer >/dev/null
  gc iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
    --member "serviceAccount:$DEPLOY_SA" --role roles/iam.serviceAccountUser >/dev/null

  echo "CI setup complete. Set these GitHub repository variables:"
  echo "  gh variable set GCP_PROJECT --body '$PROJECT'"
  echo "  gh variable set GCP_REGION --body '$REGION'"
  echo "  gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body '${pool_id}/providers/${WIF_PROVIDER}'"
  echo "  gh variable set GCP_DEPLOY_SERVICE_ACCOUNT --body '$DEPLOY_SA'"
}

build() {
  echo "==> Building $IMAGE with Cloud Build"
  gc builds submit --region "$REGION" --tag "$IMAGE" .
}

# CRM_LOCAL_IMAGE: push this already-built image (CI pushes the exact image
# its tests ran against) instead of building a new one.
push() {
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
  if [[ -n "${CRM_LOCAL_IMAGE:-}" ]]; then
    echo "==> Pushing $CRM_LOCAL_IMAGE as $IMAGE"
    docker tag "$CRM_LOCAL_IMAGE" "$IMAGE"
  else
    echo "==> Building $IMAGE with Docker and pushing it"
    docker build --platform linux/amd64 --tag "$IMAGE" .
  fi
  docker push "$IMAGE"
}

release() {
  echo "==> Deploying $IMAGE to Cloud Run service '$SERVICE'"
  # Private behind IAP (see setup). The startup probe calls /api/health, which
  # fails unless the database is reachable: a revision that never passes it
  # gets no traffic, so the previous revision keeps serving and this fails.
  # APP_VERSION is reported by /api/health; --set-env-vars replaces all vars.
  gc run deploy "$SERVICE" \
    --image "$IMAGE" \
    --region "$REGION" \
    --service-account "$RUNTIME_SA" \
    --add-cloudsql-instances "$CONNECTION_NAME" \
    --set-secrets "SDIP_DATABASE_URL=${DB_URL_SECRET}:latest" \
    --set-env-vars "APP_VERSION=${TAG},SDIP_SEED_DEMO_DATA=false" \
    --startup-probe "httpGet.path=/api/health,periodSeconds=3,failureThreshold=20,timeoutSeconds=3" \
    --min-instances 0 --max-instances "$MAX_INSTANCES" \
    --cpu 1 --memory 512Mi \
    --no-allow-unauthenticated --iap
}

# Confirms the revision running IMAGE passed its startup probe (so it is
# healthy and reached the database) and receives 100% of traffic. Prints the
# service URL last. Checks via the Cloud Run API, since IAP blocks anonymous
# HTTP requests.
verify() {
  local service
  service="$(gc run services describe "$SERVICE" --region "$REGION" --format json)"
  if ! jq -e --arg image "$IMAGE" '
      .spec.template.spec.containers[0].image == $image
      and .status.latestReadyRevisionName == .status.latestCreatedRevisionName
      and ([.status.traffic[] | select(.percent == 100) | .revisionName] == [.status.latestReadyRevisionName])
    ' <<<"$service" >/dev/null; then
    echo "Service is not serving $IMAGE from a ready revision:" >&2
    jq '{image: .spec.template.spec.containers[0].image, status: (.status | {latestCreatedRevisionName, latestReadyRevisionName, traffic})}' <<<"$service" >&2
    return 1
  fi
  echo "==> $(jq -r .status.latestReadyRevisionName <<<"$service") is healthy and serving $IMAGE"
  jq -r .status.url <<<"$service"
}

case "${1:-}" in
  setup) setup ;;
  setup-ci) setup_ci ;;
  deploy) build && release && verify ;;
  push) push ;;
  release) release ;;
  verify) verify ;;
  *) echo "Usage: GCP_PROJECT=<id> $0 {setup|setup-ci|deploy|push|release|verify}" >&2; exit 1 ;;
esac
