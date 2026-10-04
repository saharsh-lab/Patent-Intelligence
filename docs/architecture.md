# System Architecture

> Status: Phases 0–8 implemented (API, database, ingestion, baseline RAG, web UI, patent search/import, LangGraph agent, multi-source intelligence, claim-level verification). Components marked
> *(planned)* are designed but not yet built.

## 1. Goal in one sentence

Answer patent questions using evidence gathered by an **agent** that decides which
sources to consult (uploaded documents, live patent databases), and **verify every
statement** in the answer against that evidence before showing it.

## 2. End-to-end workflow

This matches the workflow in the approved project abstract:

```
User Query
   │
   ▼
Query Analyzer ─────────── what kind of question is this? (lookup / similar-search /
   │                        compare / summarise) which patents or documents are named?
   ▼
Agentic Planner ────────── which sources & tools are needed? which filters
   │                        (date range, CPC class)? semantic or keyword search?
   ▼
Multi-Source Retrieval ─── uploaded docs (pgvector)  │ EPO OPS │ USPTO │ Lens (cross-check)
   │
   ▼
Fusion, Dedup & Ranking ── merge results, remove duplicate patents (same family),
   │                        rerank with a cross-encoder, drop irrelevant ones
   ▼
Evidence Extraction ────── abstract, claims, description, citations, legal status
   │                        → chunked + embedded → hybrid (vector + keyword) retrieval
   ▼
RAG Answer Generation ──── LLM writes an answer using ONLY the numbered evidence
   │
   ▼
Claim-Level Verification ─ split answer into atomic statements; check each against
   │                        evidence; unsupported → flag, or re-retrieve and regenerate
   ▼
Final Answer + citations + grounding score + sources/tools used
```

## 3. Layers and code modules

```
frontend/  Next.js 16 UI      Login · Chat · Library · Invention analysis · Patent watch  (browser → /api/* →)
    │  HTTP/JSON (forwarded by Next.js rewrites; types generated from OpenAPI)
    ▼
backend/app/
  api/          HTTP endpoints only — validate input, call services, shape output
  services/     Use-case logic (ingest a document, answer a question, run an experiment)
  agents/       LangGraph agent: analysis.py (intent), tools.py (7 tools), graph.py (state machine)
  rag/          Chunking, embeddings, vector/keyword/hybrid search, reranking  (Phases 2–3)
  llm/          LLM providers behind one interface (fake, OpenAI-compatible/Ollama)
  patents/      PatentSource interface: EPO OPS client, demo source, cache, numbers
  evaluation/   Metrics, datasets, experiment runner                         (Phase 9)
  models/       Database tables (SQLAlchemy ORM)
  schemas/      API request/response shapes (Pydantic)
  database/     Engine, sessions, health checks
  core/         Settings, logging, errors, middleware
    │
    ▼
PostgreSQL 17 + pgvector  (Docker)
```

**Rule:** dependencies point downward only. `api` may call `services`; `rag` never
imports `api`. This keeps each part testable on its own.

## 4. Database schema (implemented in Phase 1)

```
documents 1───* chunks *───1 patents          (a chunk belongs to exactly ONE owner)
                  │
                  │ (SET NULL on delete — history survives)
                  ▼
queries 1───* agent_runs 1───* retrieval_results
                    │     1───* tool_calls
                    │     1───* claim_verifications
                    │     1───* evaluations
api_cache  (external API responses, with expiry)
```

| Table | Purpose | Key columns |
|---|---|---|
| `documents` | Uploaded files | `content_sha256` (dedup), `status`, `page_count` |
| `patents` | Records from EPO/USPTO/Lens | `publication_number`, `family_id`, `cpc_codes[]`, `claims_text`, `raw` |
| `chunks` | Searchable passages from **both** documents and patents | `embedding vector(1024)`, `tsv` (auto keyword index), `section`, `page_number` |
| `api_cache` | Avoid repeated paid/quota-limited API calls | `key`, `namespace`, `expires_at` |
| `queries` | Every question asked | `conversation_id` |
| `agent_runs` | One answer attempt by one pipeline | `pipeline`, `config` (settings snapshot), `grounding_score`, tokens, cost, latency |
| `tool_calls` | Each tool the agent invoked | `tool_name`, `success`, `latency_ms` |
| `retrieval_results` | Each passage retrieved, with score and rank | `method`, `score`, `rerank_score`, `cited_in_answer` |
| `claim_verifications` | Each answer statement and its verdict | `verdict`, `support_score`, `evidence_ids` |
| `evaluations` | Metric values per run / experiment | `experiment`, `metric_name`, `metric_value` |

### Design decisions

1. **One `chunks` table for all sources.** A single SQL query can search uploaded
   documents and fetched patents together, which is what multi-source hybrid retrieval
   needs. A `CHECK` constraint guarantees each chunk has exactly one owner.
2. **Indexes.** `HNSW` index on `embedding` (fast approximate nearest-neighbour
   search, cosine distance) and a `GIN` index on `tsv` (fast full-text search). `tsv`
   is a *generated column*, so PostgreSQL keeps it in sync with `text` automatically.
3. **Runs are separate from queries.** In experiments the same question is answered by
   several pipelines; each answer is its own `agent_run` with its exact `config`, so
   every number in the paper is traceable to how it was produced.
4. **Retrieved text is copied** into `retrieval_results`, so evaluation stays valid
   even if a document is later deleted (`chunk_id` becomes NULL; the text remains).
5. **Raw API responses are stored** (`patents.raw`) so parsing can be improved later
   without spending API quota again.
6. **Migrations (Alembic).** The schema is versioned in `backend/alembic/versions/`.
   A test runs `alembic check` so models and migrations can never drift apart.

## 5. Document ingestion pipeline (implemented in Phase 2)

```
upload (PDF/DOCX/TXT)
  │ validate: extension allow-list · real type from magic bytes · size limit · not empty
  │ SHA-256 → already ingested? return existing document (no re-embedding cost)
  │ store as data/uploads/<sha256>.<ext>   (user's filename never used as a path)
  ▼
extraction.py   pages → text blocks (PyMuPDF "blocks" keep paragraphs + page numbers)
  ▼
cleaning.py     Unicode/ligature fix · running headers & page numbers removed ·
  │             hyphenated line breaks joined · headings & claims split into own blocks
  ▼
sections.py     heading patterns → each block labelled abstract / claims / description …
  │             no headings? → section = None, citations fall back to page numbers
  │             also: title guess, patent numbers (read from the raw first page)
  ▼
chunking.py     section_aware: never crosses sections, 1 chunk per claim, ≤400 tokens,
  │             ~60-token sentence overlap · fixed: plain sliding window (baseline)
  ▼
embeddings.py   fake (tests) | local BGE-M3 | OpenAI-compatible — batched, L2-normalised
  ▼
chunks table    text = exact slice [char_start:char_end] of the cleaned document
```

`rag/ingestion.py::process_document()` runs extraction → chunking with **no database
or disk access**, so experiments can re-chunk documents with different settings.
`services/documents.py` adds storage, deduplication, embedding, and status tracking
(`processing` → `ready` | `failed` + readable reason).

**Known limitations:** scanned PDFs (no text layer) are rejected with an OCR hint;
two-column layouts rely on PyMuPDF's reading-order sort; processing runs inside the
upload request (fine for patents of a few hundred pages; a job queue is future work).

## 6. Baseline RAG pipeline (implemented in Phase 3)

```
POST /ask {question, document_ids?, top_k?, retrieval_mode?, rerank?}
  │ record Query + AgentRun(status=running, config = settings snapshot)
  ▼
retrieval.py   vector top-30 (BGE-M3, same-model chunks only) + keyword top-30 ("any word")
  │            → Reciprocal Rank Fusion → [cross-encoder rerank] → top-6
  │            every passage stored in retrieval_results (rank, method, scores)
  ▼
sufficiency gate   no passages, or best similarity < 0.35 with no keyword match
  │                → status insufficient_evidence, LLM NOT called (saves cost)
  ▼
generation.py  evidence numbered [E1]..[E6] with "source · section/claim · page" headers,
  │            within a token budget; untrusted text neutralised (delimiters, [E#], [0011]→¶0011)
  ▼
llm/providers.py   fake | OpenAI-compatible (OpenAI, Groq, OpenRouter, Ollama)
  │                tokens, latency, estimated cost recorded
  ▼
parse_answer   INSUFFICIENT_EVIDENCE? → status insufficient_evidence
  │            citations checked against the labels actually supplied
  │            (unknown label → shown as [?], listed as invalid = fabricated citation)
  │            citation coverage = cited sentences / sentences
  │            "Interpretation:" paragraph separated from evidence-backed text
  ▼
AgentRun(status=succeeded, answer JSON, cited flags on retrieval_results)
```

The user sees a safe summary ("Sources searched: Uploaded documents · 6 passages
retrieved · 3 cited"), never hidden model reasoning. Thinking output of reasoning
models is stripped.

## 7. Patent sources (implemented in Phase 5)

```
Patent Search page ── POST /patents/search ──► PatentService.search
                                                 │ for each selected source:
                                                 │   api_cache hit? → use it (no quota)
                                                 │   else PatentSource.search(PatentQuery)
                                                 │   errors isolated per source
                                                 ▼
                     EpoOpsSource: token (cached ~20 min) → CQL → /search/biblio
                     DemoPatentSource: synthetic "XX" records (opt-in)
                     (LensSource, UsptoSource: planned, same interface)

"Import as evidence" ── POST /patents/import ──► get_details (biblio + claims + description)
                                                 → patents row
                                                 → same clean/sections/chunk pipeline
                                                   (one chunk per claim) → embeddings → chunks
Ask AI ── patent_ids scope ──► hybrid retrieval over chunks (documents + patents together)
```

Design notes: every source returns the same `PatentRecord`; publication numbers are
normalised (`EP1234567A1`) so the same patent from different sources can be
deduplicated later (Phase 7, together with `family_id`); raw API responses are kept in
`patents.raw` for re-parsing without spending quota.

## 8. Agent (implemented in Phase 6)

Diagram generated from code: [agent_graph.md](agent_graph.md).

| Node | What it does |
|---|---|
| analyze | intent + patent numbers + section/claim + keywords + legal flag (rules or LLM JSON) |
| resolve_targets | numbers → imported patent / uploaded document / external; "my battery patent" → title match |
| plan | intent → tool sequence (see below) |
| execute | runs tools in order; tools may queue follow-ups (search → import top N); failures logged, not fatal |
| check | enough evidence? (direct section fetch, keyword match, or similarity ≥ threshold; for "find similar": patents found) |
| recover | ≤ `AGENT_MAX_RECOVERIES` fallback: fewer search keywords, or search all indexed sources |
| generate | numbered evidence + intent-specific instructions → LLM → citation check |
| finish | insufficient evidence / out of scope, with the reason (including tool errors) |

| Intent | Typical tool sequence |
|---|---|
| document_qa | search_uploaded_documents, or retrieve_document_section + retrieve_evidence when a section/claim of a known source is asked |
| patent_lookup | get_patent_details (if not yet imported) → retrieve_document_section/retrieve_evidence |
| find_similar | extract_key_concepts → search_patents → get_patent_details × N → compare_patents |
| compare | get_patent_details for unknown numbers → compare_patents (balanced evidence per source) |
| out_of_scope | none |

Design choices: the LLM classifies and writes; control flow is a fixed, inspectable
graph (bounded cost, testable, explainable). Every tool call is a `tool_calls` row, so
tool-selection accuracy can be measured against labelled expected tools (Phase 9).

## 9. Multi-source intelligence (implemented in Phase 7)

```
search results ─► group_by_family ─► rank_by_similarity(reference invention) ─► top N imported
                  (family ID / number)   (cosine of embeddings: title+abstract+claim 1)

compare(2–4 sources) ─► per source × aspect: preferred section passage, else most relevant
                        passage inside that source ("problem": sections only, never guessed)
                     ─► LLM JSON table  ──(invalid JSON / empty)──► extractive table (no LLM)
                     ─► validate: label exists? belongs to this cell's source?
                        similarity cites ≥ 2 sources?
                     ─► metrics: cell coverage, cross-source, fabricated, one-sided
```

Aspects: technical field, problem addressed, key components, how it works, main claim.
Extractive mode quotes the opening of the chosen passage (faithful by construction)
and lists shared vs. unique technical terms. It serves as the no-LLM baseline for
comparison experiments.

## 10. Claim-level verification (implemented in Phase 8)

```
answer ─► claims (sentences; or table cells + similarity/difference points)
       │  skip: disclaimers, "evidence does not say…", Interpretation paragraph
       ▼
pass 1: claim vs. its cited passages (each, and all cited together)
pass 2: if not supported → claim vs. all other passages
        └─ supported elsewhere ⇒ "misattributed" (counts as partial)
       ▼
verdict per claim (supported / partially / unsupported) + reason + supporting passage
grounding = (supported + 0.5·partial) / claims  → agent_runs.grounding_score,
                                                    claim_verifications rows
       ▼ (agent, VERIFY_MODE=regenerate, grounding < threshold, ≤ MAX_REGENERATIONS)
retrieve top-2 passages for each unsupported claim → rewrite with feedback → verify
→ keep the attempt with the higher grounding
```

Verifiers: NLI premise = "Source: <file/patent>, <section/claim>." + passage (the location
lets "Claim 3 adds X" be matched to the claim-3 passage). The claim is scored against the
whole passage, each sentence (claim elements split at ";") and each pair of neighbouring
sentences, and the maximum entailment counts: the small NLI model loses entailment on long
premises (found in Phase 9). The baseline pipeline verifies
but never regenerates; comparison tables are verified, not rewritten.

## 11. Evaluation framework (implemented in Phase 9)

```
experiments/configs/X.yaml ──► variants (pipeline + settings overrides, validated)
experiments/datasets/D/    ──► questions + content-based relevance labels + corpus files
        │
        ▼  python -m app.evaluation run   (separate database: patent_rag_eval)
for each variant: (re)ingest corpus if chunking/embeddings changed
    for each question × repeat: AnswerService / AgentService.ask()  ← same code as the app
        → score the stored run (scoring.py) → runs.jsonl + `evaluations` rows
        → delete patents the agent imported (no leakage between questions)
        ▼
aggregate (report.py): per-question means → bootstrap 95% CI → paired differences
        ▼
experiments/results/X/<timestamp>/  summary.json · runs.csv · report.md · environment.json
        ▼
GET /evaluations → Evaluation page
```

The runner calls the same services as the API, so the system that is measured is the system
that is demonstrated. Relevance is matched by content, not chunk ID, so the same labels
score fixed-size and section-aware chunking (Experiment B). Experiment I has its own path:
export answer statements (without system verdicts) → human labels → `verifier` command →
agreement metrics per verifier method.

## 11b. Invention analysis (added after Phase 12)

```
invention description (or an uploaded draft: abstract + claim 1)
   ▼ features.py   claim elements (split at ';' after "comprising:"), or LLM-listed features
   │               accepted only if ≥ 50% of their content words occur in the description
   ▼ (optional)    search_patents with the features' key terms → import top results
   ▼ candidates    per feature: hybrid retrieval over the whole index; documents ranked by
   │               RRF across features; the invention's own document excluded
   ▼ chart         per (feature, document): that document's top 3 passages for the feature
   │               → NLI verifier → disclosed / partially / not found + cited passage
   ▼ summary       overlap per document, features found nowhere, Markdown report
```

The chart is **computed, not generated**: the LLM never decides whether a document
discloses a feature, so the chart cannot contain an invented disclosure. Runs are stored
as `agent_runs` with `pipeline = "invention_analysis"` (no extra tables). A label-free
**self-check** (`app/evaluation/selfcheck.py`) uses each patent's own claim 1 as the
invention: with the patent searchable it should rank first with its features disclosed;
with it hidden, the closest documents should come from the same technical domain. This
scales to any number of patents without human labels.

## 11c. Accounts, conversations and memory (added after Phase 12)

```
browser ──cookie──► Next.js /api proxy ──► FastAPI
                                           │ OwnerScopeMiddleware: cookie → user (auth DB)
                                           │   → owner_scope(user_id) for the whole request
                                           ▼
   any search (baseline, agent tools, regeneration, comparison, invention analysis)
     → vector_store._apply_scope: public patents  OR  documents.owner_id = user
   patent_rag_auth (separate database): users, login_sessions
   patent_rag (main): documents.owner_id, queries.owner_id, conversations, …
```

**Conversations.** A conversation is a thread of questions (`queries.conversation_id`)
plus the documents attached in it (answers are scoped to them, "talk to this
document"). **Memory by rewriting:** each follow-up is rewritten by the LLM into a
standalone question using the last four turns ("what about claim 2?" → "What does claim 2
of US9178361B2 add?"); the rewrite is validated (non-empty, not an answer, not rambling)
and shown to the user. The rewritten question then goes through the normal
retrieve → answer → verify pipeline, so the conversation influences *what is asked* but
never serves as evidence: answers stay grounded in retrieved passages.

## 12. Cross-cutting concerns

| Concern | Implementation |
|---|---|
| Configuration | `app/core/config.py` (Pydantic Settings) reads `.env`. Secrets are `SecretStr` and never printed. |
| Request tracing | Every request gets an `X-Request-ID`; every log line includes it. |
| Logging safety | A redacting formatter masks API keys, bearer tokens, and DB passwords. |
| Errors | One JSON error shape: `{"error": {"code", "message", "request_id"}}`. No stack traces to clients. |
| CORS | Only origins listed in `CORS_ORIGINS`. |
| DB exposure | Docker binds PostgreSQL to `127.0.0.1` only. |
| Cost control | `LLM_PROVIDER=fake` / `EMBEDDING_PROVIDER=fake` for free development; `api_cache` for patent APIs. |
| Abuse & resource limits | Rate limits per endpoint group, request bodies capped while streaming, DOCX zip-bomb check (Phase 11). |
| Browser security | Security headers on API responses; CSP and anti-framing headers on the UI (Phase 11). |
| Deployment | Docker images (non-root, health checks); production start-up checks refuse example passwords, `*` CORS and demo data. Details: [security.md](security.md). |

## 13. Deviations from the abstract (to discuss with guide)

| Abstract | Current plan | Reason |
|---|---|---|
| Redis cache | PostgreSQL `api_cache` table first; Redis optional later | One less service to run; the cache interface lets Redis be swapped in. |
| Neo4j (optional) | Deferred; citations/families stored in PostgreSQL first | Only needed if graph exploration becomes a core feature. |
| USPTO / Lens | Interface ready, clients planned | EPO first (best full-text coverage for EP/WO); others added behind the same `PatentSource` interface. |
| WIPO PATENTSCOPE | At risk | Its web-service API is a paid subscription. Lens.org (which covers WO/PCT publications) is the planned substitute. |
| Next.js frontend | Next.js 16 ✅ | As in the abstract. Used mostly as a client-side app over the FastAPI backend. |
