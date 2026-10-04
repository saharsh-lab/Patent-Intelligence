# Agentic RAG-Based Patent Intelligence System

**With live multi-source patent retrieval and claim-level hallucination detection.**

B.Tech IV Year Major Project (CSE), Batch B5. Guide: Dr. T. Swathi.
Team: Kaidhapuram Saharsh Reddy, Yella Sriram Reddy, C. Manojeeth.

> Research and technical-analysis tool only. It reports *technical/semantic
> similarity* and *evidence-grounded analysis*. It is **not** legal advice and does not
> determine patent validity or infringement.

## What it does

**Accounts and chat.** Register and log in (accounts live in their own database); each
user's documents, conversations and analyses are private. Chat like a messenger:
conversations in the sidebar, attach PDFs/DOCX/TXT with 📎 or drag & drop and talk to
them, follow-up questions understood from the conversation ("and claim 2?"), answers still
cited and verified. Personal home page, light/dark theme, profile and preferences.

**Patent Watch.** Saved searches that find newly published patents, rank them against your
document and import the closest.

**New: Invention Analysis.** Describe an invention (or select an uploaded draft) and get its
technical features, the closest documents found (local and, with EPO keys, live patents),
and a feature-by-feature chart where every ✓ cites the passage that discloses the feature,
plus a downloadable report. Technical comparison only, never a novelty or infringement
opinion.

Ask questions about patents, both your uploaded documents and live records from
patent offices. An agent decides which sources to consult, gathers evidence, writes an
answer that cites each fact, and then **checks every statement against the evidence**
before showing it.

See [docs/architecture.md](docs/architecture.md) for the design,
[docs/implementation_plan.md](docs/implementation_plan.md) for the phase plan,
and [docs/concepts.md](docs/concepts.md) for plain-language explanations.

## Status

| Phase | | |
|---|---|---|
| 0 | Architecture & environment | ✅ |
| 1 | PostgreSQL + pgvector schema | ✅ |
| 2 | Document ingestion (PDF/DOCX/TXT → sections → chunks → embeddings) | ✅ |
| 3 | Basic RAG: hybrid retrieval + cited answers (`POST /ask`) | ✅ |
| 4 | Web UI: Dashboard, Documents, Ask AI with evidence, Settings | ✅ |
| 5 | Live patent search (EPO OPS), import patents as evidence | ✅ (verified against the live service, 2026-10-04) |
| 6 | Agent with tool selection (LangGraph) | ✅ |
| 7 | Multi-source intelligence: family dedup, similarity ranking, cited comparison tables | ✅ |
| 8 | Claim-level verification (hallucination detection) + regeneration | ✅ |
| 9 | Evaluation framework: labelled datasets, metrics with confidence intervals, experiment runner, Evaluation page | ✅ |
| 10 | Experiments: real-patent corpus + draft dataset, Experiment F, rehearsal of A–I | in progress (needs team label verification) |
| 11 | Hardening: rate limits, streaming size limits, zip-bomb check, security headers, production checks, Docker images, dependency audit | ✅ |
| 12 | Write-up material: diagrams, report chapter drafts, results-table generator, demo script, viva Q&A | ✅ (results chapter waits for the final runs) |
| + | Invention Analysis, Patent Watch, accounts (separate DB), private data, chat with memory and attachments, redesigned UI | ✅ |

## Tech stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 17 + pgvector 0.8 (Docker) |
| Search | pgvector HNSW (semantic) + PostgreSQL full-text (keyword) |
| Embeddings / reranker | BGE-M3, BGE reranker (local, free) *(Phase 2–3)* |
| LLM | Any OpenAI-compatible API (OpenAI, Groq, Ollama…) *(Phase 3)* |
| Agent | LangGraph state machine (analyze → plan → tools → check/recover → generate) |
| Patent data | EPO OPS, USPTO, Lens *(Phase 5)* |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, SWR |
| Testing | pytest, ruff (backend) · Vitest, ESLint, tsc (frontend) |

## Quick start

Requirements: Python 3.12, Docker Desktop, Node 20+ (from Phase 4).

```bash
make setup     # virtualenv + dependencies + creates .env from .env.example
make db-up     # start PostgreSQL + pgvector on localhost:5434
make migrate   # create the tables
make test      # run the test suite
make run       # API on http://localhost:8000  (interactive docs: /docs)
```

To use the real BGE-M3 embedding model instead of the offline fake one:

```bash
make setup-ml                      # installs PyTorch + sentence-transformers (~1 GB)
# then in .env: EMBEDDING_PROVIDER=local
make embed-check                   # first run downloads BGE-M3 (~2.3 GB)
```

To get real answers for free with a local model ([Ollama](https://ollama.com)):

```bash
ollama pull qwen3:8b
# in .env:
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3:8b
LLM_REASONING_EFFORT=none     # ~10x faster: skips Qwen3's "thinking" phase
```

Check it works: open http://localhost:8000/health/ready. You should see
`"status": "ready"` together with the PostgreSQL and pgvector versions.

### Live patent data (EPO Open Patent Services)

1. Register (free) at https://developers.epo.org, create an app, copy its consumer
   key and secret into `.env` as `EPO_OPS_KEY` / `EPO_OPS_SECRET`.
2. Restart the API. Settings → "Data sources" should list EPO.
3. Record real responses once, so tests also check the real format:
   `cd backend && .venv/bin/python -m scripts.record_epo_fixtures`

Without keys you can still try the Patent Search page with `PATENT_DEMO_SOURCE=true`
(synthetic records with country code `XX`; never use them for experiments).

Start the web UI in a second terminal:

```bash
make web-setup   # once: npm install
make web         # http://localhost:3000
```

The browser only talks to Next.js; requests to `/api/*` are forwarded to the backend
(`BACKEND_URL`, default `http://localhost:8000`; set it in `frontend/.env.local` if you
run the API on another port).

Without `make`, the same steps are:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
cp .env.example .env
docker compose up -d --wait db
cd backend && .venv/bin/alembic upgrade head && .venv/bin/pytest
.venv/bin/uvicorn app.main:app --reload
```

> Port 5434 is used because 5432/5433 are often taken by other local PostgreSQL
> installs. Change `POSTGRES_PORT` **and** the three database URLs in `.env` if needed.

## Run everything in Docker

```bash
docker compose --profile app up -d --build   # database + API + UI
# UI: http://localhost:3000   API docs: http://localhost:8000/docs
docker compose --profile app down            # stop (data is kept)
```

The API container runs migrations on start, runs as an unprivileged user, and reads
secrets from `.env`; the UI container gets none. For a local Ollama set
`DOCKER_LLM_BASE_URL=http://host.docker.internal:11434/v1` in `.env`; for local embedding /
NLI models build with `INSTALL_ML=true`. Security notes: [docs/security.md](docs/security.md).

## Evaluation (experiments)

```bash
make eval CONFIG=experiments/configs/smoke.yaml            # framework check, fake models, ~2 s
make eval CONFIG=experiments/configs/exp_a_pipelines.yaml  # baseline vs. agentic (models from .env)
```

Results go to `experiments/results/<experiment>/<timestamp>/` (summary, CSV, Markdown
report) and appear on the **Evaluation** page. Experiments use their own database
(`EVAL_DATABASE_URL`, created automatically) and never touch your uploads. See
[experiments/README.md](experiments/README.md), [docs/dataset_guide.md](docs/dataset_guide.md)
and [docs/labelling_guide.md](docs/labelling_guide.md).

## Environment variables

All configuration is in `.env` (copied from [.env.example](.env.example)). Never
commit `.env`. The defaults run fully offline and free (`LLM_PROVIDER=fake`,
`EMBEDDING_PROVIDER=fake`).

## API keys: what you need and where to get it

| Key | Needed from | Where | Cost |
|---|---|---|---|
| `EPO_OPS_KEY` / `EPO_OPS_SECRET` | Phase 5 (**primary patent source**) | Register at developers.epo.org → create an app | Free within fair-use quota |
| `LENS_API_TOKEN` | Phase 5 (cross-check) | lens.org account → request Patent API access | Free for academic/non-commercial use, on approval (**apply early**) |
| `USPTO_API_KEY` | Phase 5 (optional) | USPTO Open Data Portal (data.uspto.gov); requires identity verification | Free |
| `LLM_API_KEY` | Phase 3 | e.g. platform.openai.com, or a free-tier OpenAI-compatible provider. Not needed for a local Ollama model | Pay-per-use or free tier |
| `LANGSMITH_API_KEY` | Optional | smith.langchain.com | Free developer tier |

WIPO PATENTSCOPE's web-service API is a paid subscription, so the plan uses Lens
(which includes WO/PCT publications) instead. See `docs/architecture.md` §13.

Sign-up processes change. Check each provider's current terms, and never put keys in
code or in the frontend.

## API (so far)

| Method | Path | Description |
|---|---|---|
| GET | `/health/live` | Process is running |
| GET | `/health/ready` | Database + pgvector reachable; shows active providers/sources |
| POST | `/documents` | Upload a PDF/DOCX/TXT (multipart `file`); returns 201, or 200 + `duplicate: true` |
| GET | `/documents` | List documents with status and chunk counts |
| GET | `/documents/{id}` | One document (sections found, detected patent numbers) |
| GET | `/documents/{id}/chunks` | Chunks, optionally `?section=claims` |
| DELETE | `/documents/{id}` | Delete document, its chunks, and the stored file |
| POST | `/search/chunks` | Raw passage search: `{"query", "method": "vector"\|"keyword", "top_k"}` |
| POST | `/ask` | Answer with cited evidence: `{"question", "pipeline"?: "agentic"\|"baseline", "document_ids"?, "patent_ids"?, "top_k"?, "retrieval_mode"?, "rerank"?}`. Agentic responses include `intent`, `targets`, `steps`, `recoveries` |
| GET | `/runs` | Recent questions and their status (`?conversation_id=`) |
| GET | `/runs/{id}` | Full stored answer, evidence, and metrics for a past run |
| GET | `/patents/sources` | Which patent sources are available / not configured / planned |
| POST | `/patents/search` | Search sources: `{"keywords", "cpc"?, "applicant"?, "date_from"?, "date_to"?, "sources"?, "dedup"?: true, "rank_against_document_id"? \| "rank_against_patent_id"?}` → results with `similarity`, `also_published_as` |
| POST | `/patents/import` | Fetch a patent's full text and index it as evidence: `{"source", "publication_number"}` |
| GET | `/patents` · `/patents/{id}` | Imported patents |
| POST | `/compare` | Cited comparison table of 2–4 sources: `{"sources": [{"document_id"} \| {"patent_id"} \| {"publication_number"}], "question"?, "mode"?: "auto"\|"llm"\|"extractive"}` |
| DELETE | `/patents/{id}` | Remove an imported patent and its passages |
| POST | `/analysis/invention` | Invention analysis: `{"description"? , "document_id"?, "use_patent_search"?: true, "max_candidates"?: 5}` → features, closest documents, cited feature chart |
| GET | `/analysis/invention` · `/analysis/invention/{id}` · `/analysis/invention/{id}/report.md` | Past analyses; one analysis; Markdown report download |
| GET | `/evaluations` | Experiment results found in `experiments/results/` |
| GET | `/evaluations/{experiment}/{run}` | One result: summary (means, CIs, paired differences) + scored rows |

Full interactive docs: `http://localhost:8000/docs`.

## Project structure

```
backend/
  app/
    api/routes/   HTTP endpoints
    core/         config, logging, errors, middleware
    database/     engine/session, health check
    models/       database tables (corpus.py, runs.py)
    rag/          ingestion (extraction…chunking, embeddings), retrieval, reranker, generation
    llm/          LLM providers (fake, OpenAI-compatible incl. Ollama)
    patents/      PatentSource interface, EPO OPS client, demo source, cache, numbers
    services/     documents.py, answering.py (baseline), agent.py (agentic), patents.py,
                  comparison.py
    schemas/      API request/response models
    agents/       query analysis, tools, LangGraph agent graph
    intelligence/ family dedup, similarity ranking, structured comparison
    verification/ claim extraction, NLI / LLM-judge / lexical verifiers, grounding score
    evaluation/   datasets, metrics, scoring, experiment runner, verifier evaluation (CLI)
  alembic/        database migrations
  tests/
frontend/
  src/app/        pages: dashboard, documents, ask, settings (+ planned-feature pages)
  src/components/ AppShell, ui primitives, ask/ (answer, evidence, workspace)
  src/lib/        typed API client, citation parser, formatters (+ unit tests)
  src/types/      api.d.ts generated from the backend OpenAPI schema
docs/             architecture, plan, concepts, methodology, evaluation, security,
                  observations (findings), dataset/labelling guides, demo script, viva Q&A
  diagrams/       Mermaid sources + rendered SVG/PNG figures for the report and slides
  report/         report chapter drafts (results are placeholders until the final runs)
docker/           database init script
experiments/      datasets, experiment configs, human labels, results (see experiments/README.md)
```

## Known limitations (current)

- The EPO client is tested against real recorded OPS v3.2 responses (2026-10-04) and the
  live service; Lens and USPTO clients are not built.
- Only EPO is implemented; Lens and USPTO clients are planned. Full text (claims,
  description) is only available from EPO for some offices (EP, WO, and a few others).
- Claim verification is automatic and imperfect: the small NLI model is strict and can flag
  paraphrases or claims that combine passages (false alarms). Its accuracy against human labels is
  measured by Experiment I (needs labels from the team).
- The only dataset so far (`experiments/datasets/dev`) is synthetic and AI-written: it tests the
  evaluation framework, and its numbers must not be reported.
- Accounts have no email verification or password reset by email (no mail server); serve
  over HTTPS (reverse proxy) before exposing the app to a network (docs/security.md).
- Scanned PDFs without a text layer are rejected (no OCR).
- Section detection relies on standard patent headings; other layouts fall back to
  page-level citations.
- Embedding size is fixed at 1024 (BGE-M3) in the first migration; a different
  model size needs a new migration and re-embedding.
