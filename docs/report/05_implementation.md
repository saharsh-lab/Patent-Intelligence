# 4. Implementation

## 4.1 Development approach
The system was built in thirteen phases (0–12), each ending with automated tests and a
manual check with real models, followed by improvements prompted by user testing
(live and web search, verifier stages, a single asking page). The backend has 405 automated tests (unit tests with
fake models, and integration tests against a separate PostgreSQL test database rolled back
after each test); the frontend has 37 unit tests, type checks and linting, and pages were
checked in a real browser. Tests never reach live services: patent-office credentials and
web search are switched off in the test setup.

## 4.2 Backend modules
| Module | Content |
|---|---|
| `rag/` | extraction (PyMuPDF, python-docx), cleaning, section detection, chunking, embeddings, vector and keyword search, RRF fusion, reranker, prompt construction and answer parsing |
| `agents/` | query analysis (rules and LLM, small talk), nine tools, LangGraph agent |
| `verification/` | NLI, lexical and LLM-judge verifiers, NLI + lexical rescue, LLM second opinion, patent-number attribution guard; claim extraction; two-pass checking |
| `web/` | web search providers (Tavily, Wikipedia) |
| `invention/` | invention analysis: feature extraction, candidate ranking, feature chart, Markdown report |
| `intelligence/` | patent family de-duplication, similarity ranking, structured comparison tables |
| `patents/` | EPO OPS client (OAuth, CQL search, full text), demo source, response cache |
| `evaluation/` | dataset format, metrics, scoring, experiment runner, verifier evaluation, reports |
| `services/`, `api/` | baseline and agentic answer services, documents, patents, comparison; HTTP routes |
| `core/` | configuration, logging with secret redaction, errors, security middleware, one lock around all local model inference |

## 4.3 Key algorithms
**Section-aware chunking.** Headings are matched against patent section names; claims are
split at their numbers ("1.", "2." …) into one chunk each; other sections are packed
paragraph by paragraph up to the token limit with overlap. Exact `char_start`/`char_end`
offsets are kept for every chunk.

**Hybrid retrieval.** `vector_search` (pgvector cosine distance, HNSW, filtered by
embedding model) and `keyword_search` (PostgreSQL full text: the question's stemmed words combined with OR, ranked by `ts_rank_cd` (cover density), GIN index) each
return 30 candidates; RRF with k = 60 merges them.

**Answer parsing.** Citations `[E#]` are validated against the evidence given; invalid
labels are removed and counted; citation coverage = cited sentences / sentences; the
"Interpretation:" paragraph is separated; "INSUFFICIENT_EVIDENCE" with missing information
is recognised.

**Verification.** See Section 3.5. The NLI model is `cross-encoder/nli-deberta-v3-xsmall`;
label order is read from the model configuration.

**Transient passages.** Web results and patent-office hits are wrapped in an object that
behaves like a stored passage for generation and verification (text, section, source
label, link) but has no database row; run records keep their text without a chunk link,
and the answer's evidence lists their site or publication number and URL.

**Model inference on the GPU.** On Apple silicon, PyTorch's MPS backend aborted the whole
process when two requests ran models at once (reproduced with six concurrent threads).
One process-wide lock now serialises every embedding, reranking and NLI call; requests
wait a moment instead of crashing.

**Comparison.** For 2–4 sources, evidence is retrieved per source (balanced), and a table
of technical aspects × sources is generated (LLM, JSON-validated) or extracted; every cell
must cite its own source's passages, and cross-source citations are removed and counted.

**Invention analysis.** For F features and D candidate documents, F·D scoped retrievals
(top 3 passages each) are judged in a single batched verifier call; with the defaults
(≤ 8 features, 5 documents) that is at most 40 cells. Each cell records verdict, score and
the passage; runs are stored like answers (agent runs with tool steps and cited
retrieval results) and exported as a Markdown report.

## 4.4 Frontend
The UI is built around one asking page, like the assistants users already know. A new
chat opens on a search-style start screen (greeting, a large question box with attach and
"Patent DBs" controls, suggested questions, shortcuts to the tools) and becomes a
conversation once a question is asked, with the box docked below. After login, a
sidebar lists the user's conversations (grouped by date, renamable) and three tools:
**Library** (My documents, Find patents, Compare), **Invention analysis** (feature chart
with clickable evidence and report download) and **Patent watch** (new-publication alerts
with an unread badge). A chat answers with clickable citations and a one-line trust
summary ("5 of 6 statements verified"); sources (documents, patents and web pages, each
with a link), sentence checks and the agent's steps open on demand. Greetings get a short
reply without retrieval. Files are attached by drag-and-drop or the paperclip, and any library
item opens a chat with it attached. Follow-ups are shown with the standalone question
the system understood. Research pages (Evaluation results with confidence intervals,
a Research console exposing every retrieval option, System status) sit in the user menu,
with the profile (including the balanced/strict hallucination-check setting) and the
light/dark theme. API types are generated from the backend's
OpenAPI schema.

## 4.5 Security and deployment
Configuration and secrets come from `.env` (secrets as `SecretStr`, never logged or sent to
the browser); uploads are validated by content, size-limited while streaming and checked
for zip bombs; rate limits cap LLM-backed requests; security headers and a
Content-Security-Policy protect the UI; production start-up refuses unsafe settings.
Docker images (non-root, health checks) run the full stack with one command; on a laptop,
`make demo` starts the API and UI with the local models. Details and remaining risks:
docs/security.md.

## 4.6 Tools and versions
Python 3.12, FastAPI 0.142, SQLAlchemy 2.1, LangGraph 1.2, PyMuPDF 1.28,
sentence-transformers 6.1, PostgreSQL 17, pgvector 0.8.7, Next.js 16, React 19,
Ollama with Qwen3-8B. Exact versions: backend/requirements*.txt, frontend/package.json, and
`environment.json` in each experiment result.
