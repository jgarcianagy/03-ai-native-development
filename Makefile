.PHONY: run run-frontend test test-frontend test-integration test-e2e gcp-setup gcp-setup-ci gcp-deploy

run:
	cd backend && uv run --with-requirements requirements.txt uvicorn app.main:app --reload --port 8091

run-frontend:
	cd _frontend && python3 -m http.server 8092

test:
	cd backend && uv run --python 3.12 --with-requirements requirements-dev.txt pytest

test-frontend:
	cd _frontend && node run-tests.mjs

# Builds and starts an isolated copy of docker-compose.yaml (port 18001,
# throwaway volume), runs the HTTP tests against it, then tears it down.
test-integration:
	cd integration_tests && uv run --with 'pytest>=8,<9' --with 'httpx>=0.27,<1' pytest

# Browser tests against the same isolated stack: starts it, runs Playwright
# (installs Chromium on first run), tears it down.
COMPOSE_TEST = docker compose -p crm-integration-tests -f docker-compose.yaml -f integration_tests/docker-compose.test.yaml
E2E_UV = uv run --with 'pytest>=8,<9' --with 'pytest-playwright>=0.7,<1' --with 'httpx>=0.27,<1'
test-e2e:
	$(COMPOSE_TEST) up -d --build --wait
	cd e2e_tests && $(E2E_UV) playwright install chromium && $(E2E_UV) pytest; \
		status=$$?; cd .. && $(COMPOSE_TEST) down -v; exit $$status

# Google Cloud (Cloud Run + Cloud SQL). Requires GCP_PROJECT (and CRM_IAP_MEMBERS
# for gcp-setup); see _docs/deploy-gcp.md.
gcp-setup:
	./deploy/gcp.sh setup

# One-time: lets GitHub Actions deploy via OIDC. Also requires GITHUB_REPO=owner/name.
gcp-setup-ci:
	./deploy/gcp.sh setup-ci

gcp-deploy:
	./deploy/gcp.sh deploy
