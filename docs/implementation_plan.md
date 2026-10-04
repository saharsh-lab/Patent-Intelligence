# Implementation Plan

Two semesters, 13 phases. Each phase ends with working code, passing tests, and a short
demo. A phase is **done** only when its "Done when" checks pass.

| Phase | Name | Semester | Status |
|---|---|---|---|
| 0 | Architecture & environment | VII | ✅ Done |
| 1 | PostgreSQL + pgvector schema | VII | ✅ Done |
| 2 | Document ingestion | VII | ✅ Done |
| 3 | Basic RAG (hybrid retrieval + grounded answer) | VII | ✅ Done |
| 4 | Frontend + backend integration | VII | ✅ Done |
| 5 | Patent API integration (EPO OPS first) | VII | ✅ Done (live check pending keys) |
| 6 | Agent & tools (LangGraph) | VII → VIII | ✅ Done |
| 7 | Multi-source fusion, dedup, reranking | VIII | ✅ Done |
| 8 | Evidence, citations & claim-level verification | VIII | ✅ Done |
| 9 | Evaluation framework | VIII | Next |
| 10 | Experiments & analytics | VIII | |
| 11 | Testing, security, performance, Docker | VIII | |
| 12 | Documentation & research artifacts | VIII | |

Suggested milestone for the end of Semester VII review: Phases 0–5 complete, with a
demo of upload → ask → cited answer, plus a live EPO patent search.

---

### Phase 0 — Architecture & environment ✅
Built: project structure, FastAPI app factory, settings from `.env`, request-ID
middleware, redacting logger, uniform JSON errors, CORS, `/health/live` and
`/health/ready`, Docker Compose for PostgreSQL + pgvector, Makefile, pytest + ruff.
**Done when:** `make test` passes; `/health/ready` returns `ready` with the DB up and
503 with it down. ✔

### Phase 1 — Database ✅
Built: 10 tables (see `architecture.md` §4), Alembic migration `0001`, HNSW + GIN
indexes, `vector_search()` and `keyword_search()` in `app/rag/vector_store.py`.
**Done when:** migration upgrades, downgrades, and re-upgrades cleanly;
`alembic check` reports no drift; search and constraint tests pass. ✔

### Phase 2 — Document ingestion ✅
Built: upload validation (extension allow-list, magic-byte type check, size limit,
SHA-256 dedup, safe storage names), extraction (PyMuPDF blocks with page numbers,
python-docx incl. tables, TXT with encoding fallback), cleaning (running headers,
page numbers, hyphenation, ligatures), patent section detection with graceful
fallback, title + patent-number detection, section-aware and fixed chunking,
embedding providers (fake / local BGE-M3 / OpenAI-compatible), endpoints
`POST/GET /documents`, `GET/DELETE /documents/{id}`, `GET /documents/{id}/chunks`,
and a debugging endpoint `POST /search/chunks` (vector or keyword).
**Done when:** synthetic patent TXT/PDF/DOCX ingest with all sections detected,
one chunk per claim, correct page numbers; invalid/empty/oversized/scanned files
rejected with clear errors; ingestion failure leaves a `failed` record that can be
retried; full test suite passes. ✔

### Phase 3 — Basic RAG ✅
Built: hybrid retrieval (pgvector + full-text "any word" matching, fused with
Reciprocal Rank Fusion), optional cross-encoder reranker, retrieval-level
sufficiency gate (no LLM call when nothing relevant is found), numbered-evidence
prompt with injection hardening, LLM providers (fake / any OpenAI-compatible incl.
local Ollama), answer parser (citation validation, fabricated-label detection,
citation coverage, "Interpretation:" separation), `POST /ask`, `GET /runs`,
`GET /runs/{id}`. Every run stores query, settings snapshot, retrieved passages
with scores and cited flags, tokens, cost and per-step timings.
**Done when:** answered / model-insufficient / gate-insufficient / LLM-failure paths
all tested; verified end-to-end with BGE-M3 + Qwen3-8B (see `observations.md`). ✔
This pipeline is the **control condition for Experiment A**.

### Phase 4 — Frontend ✅
Built with **Next.js 16** (as in the abstract), React 19, TypeScript, Tailwind CSS 4
and SWR. Pages: Dashboard (counts, system status, recent questions), Documents
(drag-and-drop upload with per-file results, library table, document detail with
passages filterable by section), Ask AI (scope selection, retrieval options, answer
with clickable citation chips, separated "model interpretation", insufficient-evidence
and failure states, run summary and metrics, evidence cards with scores, history),
Settings (read-only config from new `GET /system/info`, which never exposes secrets),
and honest placeholders for Patent Search / Comparison / Evaluation.
Next.js forwards `/api/*` to FastAPI (no CORS, backend URL server-side only).
API types are generated from the backend's OpenAPI schema (`npm run gen:api`).
**Done when:** typecheck, lint, 12 unit tests and production build pass; verified in
Chrome with Playwright: upload → ask (Qwen3) → click citation → evidence highlighted;
invalid upload shows readable error; phone width has no horizontal overflow; dark
mode renders. ✔

### Phase 5 — Patent APIs ✅ (live verification pending EPO keys)
Built: `PatentSource` interface; EPO OPS v3.2 client (OAuth token caching, CQL query
builder for keywords/CPC/applicant/date range, search, biblio + claims + description,
404 = no results, fair-use 403 with `X-Rejection-Reason`); publication-number
normalisation (`EP 1 234 567 A1` → `EP1234567A1`, docdb `EP.1234567.A1`); PostgreSQL
response cache (`api_cache`, 1-week TTL); per-source error isolation; import that
stores the patent and indexes title/abstract/claims/description through the same
chunking pipeline (one chunk per claim); Ask AI scoping by imported patents with
source badges and Espacenet links; Patent Search page; opt-in demo source of
synthetic patents. Lens and USPTO remain planned behind the same interface.
**Verified:** 30 new tests (mock HTTP server, hand-made OPS JSON); browser flow
search → import → ask with the demo source and Qwen3. **Pending:** run
`scripts/record_epo_fixtures.py` with real keys; the recorded-response test then runs.

### Phase 6 — Agent & tools ✅
Built: LangGraph state machine `analyze → resolve_targets → plan → execute → check →
(generate | recover → execute | finish)` (diagram: `docs/agent_graph.md`); query
analysis by rules or LLM (JSON, validated, patent numbers must occur in the question,
partial acceptance when the LLM invents an intent); 5 intents (document Q&A, patent
lookup, find similar, compare, out of scope) + legal-question flag; target resolution
(publication numbers → imported patent / uploaded document / external; "my battery
patent" → title match among uploaded documents, never guessing between several);
7 tools (search_uploaded_documents, retrieve_evidence, retrieve_document_section,
search_patents, get_patent_details, compare_patents, extract_key_concepts); per-tool
logging to `tool_calls`; bounded recovery (fewer keywords, broaden scope); intent-
specific answer instructions; legal questions reframed as technical comparisons with a
disclaimer; token usage summed over all LLM calls; `pipeline` switch on `/ask`
(agentic default, baseline kept for Experiment A); UI panel "How this answer was produced".
**Verified:** 40 new tests (tool selection per intent, recovery, failures, out-of-scope,
token accounting); real runs with Qwen3-8B + BGE-M3 + demo patents (see observations).

### Phase 7 — Multi-source intelligence ✅
Built: patent-family deduplication (family ID, else number without kind code;
representative prefers EP/WO full text, granted, newer) with "also published as";
semantic similarity ranking of candidates against an invention (title + abstract +
claim 1, embedding cosine) used by Patent Search ("rank against") and by the agent
(imports the most similar, not the first returned); structured comparison of 2–4
sources (5 aspects × sources table + similarities + differences) in LLM mode (JSON,
validated) or extractive mode (no LLM; also the automatic fallback), with grounding
metrics: cell coverage, cross-source citations, fabricated citations, one-sided
similarities; `POST /compare`; the agent's compare intent produces the same table;
Comparison page; table also shown in Ask AI.
**Verified:** 16 new tests; real comparison with Qwen3 (3 sources, 53 s, all
citation metrics clean, yet one cell's content not supported by its cited passage;
see observations). Also fixed a flaky vector-search test (HNSW dead entries in the
test DB → VACUUM per session) and added pgvector iterative scans as a safeguard.

### Phase 8 — Claim-level verification ✅
Built: claims = answer sentences (disclaimers, statements about missing evidence and the
"Interpretation:" paragraph skipped) or comparison cells/points; three verifiers: NLI
(cross-encoder/nli-deberta-v3-xsmall, local), LLM judge (one call per answer), lexical
(word overlap baseline); two-pass check (cited passages, individually and combined →
all other passages, which detects *misattributed* claims); passages given to the
verifier with their location ("Source: battery.txt, claim 3"); grounding score =
(supported + 0.5 × partial) / claims, stored per run plus one `claim_verifications` row
per claim linked to retrieval results; agent graph `generate → verify → (regenerate:
retrieve evidence for unsupported claims, rewrite with feedback → verify)`, keeping the
better-grounded attempt; baseline verifies but never regenerates; `VERIFY_MODE`
off/report/regenerate for Experiment G; UI: sentence highlighting by verdict,
verification panel with attempt history, ✓/~/✗ on comparison cells, Grounding metric.
**Verified:** 21 new backend + 2 frontend tests (planted hallucination detected and
regenerated away; worse regeneration discarded; baseline never regenerates); real runs
with Qwen3 + NLI (see observations).

### Phase 9 — Evaluation framework ✅
Built: YAML dataset format with content-based relevance labels (document + quote / claim /
section, so labels survive re-chunking), key facts, expected intent/tools, legal flag,
answerable flag; strict validation (typos rejected); metrics (precision/recall@k, MRR,
hit@k, context precision/recall, key-fact recall, answer-vs-abstain correctness, citation
coverage, grounding, unsupported and misattribution rates, regeneration gain, intent and
tool precision/recall, latency, tokens, cost); per-question averaging, 95% bootstrap CIs,
paired differences with a "clear" flag; runner (`python -m app.evaluation run`) on a
separate `patent_rag_eval` database, with per-variant validated settings, corpus
re-ingestion only when chunking/embeddings change, imported patents cleared between
questions, incremental `runs.jsonl`, abort after 3 consecutive failures, automatic
warnings (fake models, synthetic data, small n); result folder with config, environment,
rows, summary, Markdown report; threshold sweep for `RETRIEVAL_MIN_SIMILARITY`;
Experiment I tooling (export statements without system verdicts → human labels →
accuracy, κ, detection P/R/F1, confusion matrices); configs for A, B, C, D, G, H, I;
synthetic dev set (20 questions); dataset and labelling guides; `/evaluations` API and
Evaluation page.
**Verified:** 49 new backend tests (metrics vs. hand-computed values, dataset/config
validation, full runner, export → label → verifier scoring, API, regression tests for the
fixes below) + 5 frontend tests; Evaluation page checked in the browser (desktop, phone,
dark). Running the framework found and fixed: two rule-planner gaps and one wrong dev
label (smoke run); an NLI verifier bug that lowered grounding on multi-sentence passages
(sentence windows added); LLM-planner wrong refusals and invented sections (guards added).
Experiment A was run twice end to end with Qwen3 + BGE-M3 + NLI on the dev set (see
observations).

### Phase 10 — Experiments (in progress)
Done: `AGENT_TOOL_POLICY=all` (Experiment F control) + config; `scripts/build_corpus.py`
(public patents → clean text); `real_v1` draft dataset (16 real patents, 54 questions,
labels drafted by the AI assistant); label tooling (`--check-labels` under both chunkings,
key-fact check, `review` sheet, `rescore` without model calls, `run --dataset`); content
anchors for claim/section labels (fixed a bias against fixed-size chunking); rehearsal of
the experiment suite on the dev set; Experiment A on the draft real dataset; document-level
source metrics; interleaved + counterbalanced variant order with a warm-up question and a
timed planner step (latency confounds found in the rehearsal); LLM-planner guard against
spurious similar-patent searches (found on real patents).
Waiting on the team: verify `real_v1` (two people) and split dev/test; label statements
for Experiment I; choose the LLM for reported runs; EPO keys for Experiment E.

### Phase 11 — Hardening ✅
Built: rate limits (LLM / ingest / default budgets, 429 + Retry-After, spoof-resistant
client identity); request-body limits enforced while streaming; DOCX zip-bomb check;
security headers on API and UI (CSP in production builds); production start-up checks;
Dockerfiles (non-root, health checks, migrations on start) + `app` compose profile;
dependency audit (pip-audit, npm audit: no known vulnerabilities); docs/security.md.
**Verified:** 10 new tests; full stack built and run in Docker (upload → ask → answer
through the UI proxy, headers, non-root users, no secrets in the UI container); UI loaded
in a browser under the production CSP without console errors.

### After Phase 12 — Product features ✅
Invention Analysis (computed, cited feature chart; label-free self-check); Patent Watch
(monitoring of new publications); accounts in a separate database (scrypt, server-side
sessions, rate-limited login); per-user data isolation enforced in the search layer;
chat conversations with question-rewriting memory and in-chat document upload; redesigned,
personalised UI (sidebar with chats, home page, profile, light/dark theme, mobile drawer).
**Verified:** 350 backend tests (incl. cross-user isolation through listing, search,
questions, chats; separate copies for identical uploads; first-account adoption), 25
frontend tests, full browser journey with real models (register → chat with attached
patent → follow-up rewritten → sources → dark theme → logout → second user sees nothing).
Found and fixed: proxy timeout shorter than slow answers (chat now recovers), a test that
could reach the development database (all database URLs now forced to test databases).

### Phase 12 — Write-up ✅
Built: seven diagrams (architecture, ingestion, answer flow, verification, NLI judgement,
evaluation, database) as Mermaid sources with rendered SVG/PNG; regenerated agent graph;
results-table generator (`python -m app.evaluation tables`, Markdown or LaTeX, CIs and
† for clear differences, warnings carried into the table); report chapter drafts
(abstract → conclusion, references to verify); demo script with questions tested on real
patents; viva Q&A (38 questions). **Waiting on the team:** final results (after label
verification and test questions), then the results, discussion and abstract numbers.

---

## Open decisions

1. ~~Frontend framework~~ — decided: Next.js (matches the abstract).
2. **LLM provider.** Qwen3-8B via Ollama (local, free) works well for development.
   Before experiments, fix ONE model (local or API) and use it for all reported runs.
3. **WIPO PATENTSCOPE.** Confirm with guide that Lens can stand in for it.
