# Common commands. Run `make help` to list them.
PY := backend/.venv/bin

.PHONY: help demo setup setup-ml embed-check web-setup web web-test gen-api db-up db-down db-reset db-shell migrate test lint format run eval eval-dry eval-validate eval-export eval-live-build eval-live eval-agreement eval-verifier eval-review eval-rescore eval-tables

help:  ## List available commands
	@grep -E '^[a-z-]+:.*##' Makefile | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup:  ## Create the Python virtualenv and install dependencies
	python3.12 -m venv backend/.venv
	$(PY)/pip install -r backend/requirements-dev.txt
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

setup-ml:  ## Install local embedding models support (PyTorch, ~1 GB)
	$(PY)/pip install -r backend/requirements-ml.txt

embed-check:  ## Check the configured embedding model on sample sentences
	cd backend && .venv/bin/python -m scripts.check_embeddings

db-up:  ## Start PostgreSQL + pgvector (Docker)
	docker compose up -d --wait db

db-down:  ## Stop the database (data is kept)
	docker compose down

db-reset:  ## DELETE all database data and start fresh
	docker compose down -v && docker compose up -d --wait db && $(MAKE) migrate

db-shell:  ## Open a psql shell in the database
	docker exec -it patent_rag_db psql -U patent_rag -d patent_rag

migrate:  ## Apply database migrations (patent data + separate accounts database)
	cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m scripts.migrate_auth

test:  ## Run all backend tests
	cd backend && .venv/bin/pytest

lint:  ## Check code style
	cd backend && .venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests

format:  ## Auto-format code
	cd backend && .venv/bin/ruff check --fix app tests && .venv/bin/ruff format app tests

demo:  ## Start everything with the real local models (API :8100, UI :3000); needs Ollama + make db-up
	./scripts/demo.sh

run:  ## Start the API at http://localhost:8000 (docs at /docs)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

web-setup:  ## Install frontend dependencies
	cd frontend && npm install

web:  ## Start the web UI at http://localhost:3000 (needs `make run` too)
	cd frontend && npm run dev

web-test:  ## Typecheck, lint and unit-test the frontend
	cd frontend && npm run typecheck && npm run lint && npm test

gen-api:  ## Regenerate frontend API types after backend changes
	cd frontend && npm run gen:api

# --- Evaluation (Phase 9). Example: make eval CONFIG=experiments/configs/smoke.yaml
CONFIG ?= experiments/configs/smoke.yaml

eval:  ## Run an experiment: make eval CONFIG=experiments/configs/<name>.yaml
	cd backend && .venv/bin/python -m app.evaluation run --config ../$(CONFIG)

eval-dry:  ## Validate an experiment config without running it
	cd backend && .venv/bin/python -m app.evaluation run --config ../$(CONFIG) --dry-run

eval-validate:  ## Check a dataset: make eval-validate DATASET=experiments/datasets/dev/dataset.yaml
	cd backend && .venv/bin/python -m app.evaluation validate --dataset ../$(DATASET)

eval-export:  ## Export statements for labelling: make eval-export RESULT=experiments/results/<exp>/<run>
	cd backend && .venv/bin/python -m app.evaluation export-claims --result ../$(RESULT) --sample 150

eval-live-build:  ## Experiment E step 1: fetch new patents live from EPO, freeze the questions
	cd backend && .venv/bin/python -m app.evaluation live-build --config ../experiments/configs/exp_e_live.yaml

eval-live:  ## Experiment E step 2: live vs local-only vs closed-book answers
	cd backend && .venv/bin/python -m app.evaluation live-run --config ../experiments/configs/exp_e_live.yaml

eval-agreement:  ## Compare two labellers: make eval-agreement LABELS=experiments/labels/test_claims
	cd backend && .venv/bin/python -m app.evaluation agreement --a ../$(LABELS)_A.csv --b ../$(LABELS)_B.csv --out ../$(LABELS).csv

eval-verifier:  ## Score verifiers against human labels (Experiment I)
	cd backend && .venv/bin/python -m app.evaluation verifier --config ../experiments/configs/exp_i_verifiers.yaml

eval-review:  ## Review sheet for verifying a dataset: make eval-review DATASET=experiments/datasets/real_v1/dataset.yaml
	cd backend && .venv/bin/python -m app.evaluation validate --dataset ../$(DATASET) --check-labels && .venv/bin/python -m app.evaluation review --dataset ../$(DATASET)

eval-rescore:  ## Re-score a result with the current labels (no model calls): make eval-rescore RESULT=...
	cd backend && .venv/bin/python -m app.evaluation rescore --result ../$(RESULT)

eval-tables:  ## Results table for the report: make eval-tables RESULT=experiments/results/<exp>/<run> FORMAT=latex
	cd backend && .venv/bin/python -m app.evaluation tables --result ../$(RESULT) --format $(or $(FORMAT),markdown)
