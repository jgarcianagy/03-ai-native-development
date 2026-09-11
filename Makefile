.PHONY: run test

run:
	cd backend && uv run --with-requirements requirements.txt uvicorn app.main:app --reload --port 8091

test:
	cd backend && uv run --with-requirements requirements.txt pytest
