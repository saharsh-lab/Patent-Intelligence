# Security review (Phase 11)

## Threat model

**What the system is:** a single-user research tool. It runs on a laptop, or a small server
the team controls, with the Next.js UI in front of the FastAPI backend.

**What we protect:**
- third-party API keys (EPO, LLM provider);
- the database;
- the machine's resources (disk, CPU, paid LLM calls);
- the people using the UI.

**Accounts (added after Phase 12):** users register and log in; every document,
conversation, analysis, watch and question belongs to its user. A reverse proxy is still
needed for HTTPS when the app is exposed to a network.

## Requirements from the project brief

| Requirement | Implementation | Verified by |
|---|---|---|
| `.env` configuration | `app/core/config.py` (Pydantic Settings); `.env` is git-ignored; `app/core/config.py` documents every variable | — |
| No hard-coded secrets | Keys exist only as `SecretStr` settings read from the environment; prints as `**********` | tests (Phase 0) |
| Never log secrets | Redacting log formatter masks API keys, bearer tokens, DB passwords (`app/core/logging.py`); request logs hold method, path, status and time only | tests (Phase 0) |
| Secrets never reach the frontend | The browser only calls the Next.js server; `/api/*` is proxied server-side; `/system/info` returns an allow-list of harmless values; in Docker, the web container receives no secrets | `/system/info` test; `docker exec rag-web-1 env` check (Phase 11) |
| File validation | Extension **and** content checked (PDF magic bytes, DOCX = ZIP containing `word/document.xml`, TXT without NUL bytes); renamed executables rejected; filenames sanitised; files stored under their SHA-256, never under user-chosen names | tests (Phase 2) |
| Upload limits | `MAX_UPLOAD_MB` enforced **while the body streams in**, before parsing (`BodySizeLimitMiddleware`); `MAX_PDF_PAGES`; DOCX zip-bomb check (expanded size, entry count, compression ratio) | `test_phase11_security.py` |
| Input validation | Pydantic schemas with length/range limits on every request (question ≤ 2,000 chars, ≤ 50 scope IDs, top_k ≤ 20, …); non-upload bodies ≤ `MAX_JSON_BODY_KB` | tests (Phases 3–7, 11) |
| CORS | Only the origins in `CORS_ORIGINS`; no credentials; fixed method/header lists; `*` refused in production | Phase 0 + production check |
| API key protection | Keys used only server-side in the patent and LLM clients; never in URLs, logs or responses; EPO tokens kept in memory | Phase 5 tests |

## Accounts and data isolation

| Measure | What it prevents | Where |
|---|---|---|
| Accounts in a **separate database** (`patent_rag_auth`, own migrations) | A breach or bug in the patent data layer exposing credentials; mixing personal data with research data | `app/auth/`, `alembic_auth/` |
| scrypt password hashing with per-user salt, constant-time comparison; password rules | Cracking stolen hashes; timing attacks | `app/auth/passwords.py` |
| Server-side sessions: random 256-bit token in an **httpOnly, SameSite=Lax** cookie (Secure in production); only its SHA-256 stored; logout revokes; password change logs out other browsers | XSS stealing the session, CSRF, replay of a leaked database or an old cookie | `app/auth/service.py`, `routes.py` |
| Identical error for unknown email and wrong password; dummy hash check for unknown emails; 10 login attempts/min | Account enumeration, password guessing | same, `core/security.py` |
| **Owner scope per request**: a middleware identifies the user, and the search layer only returns public patents and that user's documents | One user seeing another's documents through any path: listing, search, agent tools, comparisons, invention analysis | `app/auth/middleware.py`, `app/core/ownership.py`, `rag/vector_store.py` |
| Duplicates detected **per owner**; shared stored files deleted only when unused | User B receiving user A's document by uploading the same file; deleting another user's file | `services/documents.py`, migration 0003 |
| "Not found" for other users' resources (not "forbidden") | Learning that a given id exists | routes, services |
| Login redirect only to internal paths | Open redirect after login | `frontend/src/components/auth/AuthForm.tsx` |

## Added in Phase 11

| Measure | What it prevents | Where |
|---|---|---|
| Rate limits: 20/min for `/ask` and `/compare`, 30/min for uploads and patent API calls, 600/min otherwise; 429 + `Retry-After` | Runaway LLM cost, hammering the EPO quota, accidental loops | `app/core/security.py` |
| Body-size limit before parsing | Filling the disk or memory with a huge (or chunked) upload | same |
| DOCX zip-bomb check | A 50 KB file that expands to gigabytes when unpacked | `app/rag/extraction.py` |
| API security headers: `nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`, `CSP: default-src 'none'`, HSTS in production | Browsers interpreting JSON as HTML, framing, caching answers about private documents | `app/core/security.py` |
| UI security headers + Content-Security-Policy (production builds); no `X-Powered-By` | Clickjacking, loading scripts or connecting to other origins, plugins | `frontend/next.config.ts` |
| Production start-up checks: refuse the example DB password, `CORS_ORIGINS=*`, demo patents, or disabled rate limits; warn on fake models | Deploying laptop settings by mistake | `check_production_settings` |
| Containers run as an unprivileged user; ports bound to 127.0.0.1; the DB is not published in the app profile | Escalation from a compromised process; exposure to the local network | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` |
| Dependency audit | Known-vulnerable packages | `pip-audit`: none found; `npm audit --omit=dev`: 0 vulnerabilities (2026-10-04) |

### Design notes for the viva
- **Why rate limits ignore `X-Forwarded-For` by default:** the bundled Next.js proxy keeps
  any `X-Forwarded-For` the browser sends, so trusting it would let a client claim a fresh
  identity on every request (tested). Behind the proxy, all browser traffic therefore shares
  one budget. That is fine for a single-user tool and acts as a cost guard. Set
  `TRUST_PROXY_HEADERS=true` only behind a proxy that overwrites the header.
- **Why check size while streaming:** the multipart parser writes an upload to disk before
  the route can check its size, and a chunked request has no `Content-Length` to check in
  advance.
- **Why the UI's CSP allows inline scripts:** Next.js hydrates pages with inline scripts;
  forbidding them would need per-request nonces. The policy still blocks other origins,
  framing and plugins.

## Risks that remain (state them honestly)

1. **No email verification or password reset by email** (no mail server); no
   multi-factor login. Accounts are for separating users' data, not for an Internet-facing
   service.
2. **Prompt injection.** Patent text is untrusted input to the LLM. Mitigations: evidence is
   wrapped and labelled as data, not instructions (`format_evidence`); the model has no
   tools that can modify data; every answer sentence is verified against the evidence.
   A crafted document can still steer the wording of an answer about itself.
3. **Model downloads.** Hugging Face models (BGE-M3, NLI, reranker) are downloaded on first
   use from their official repositories and trusted. For a production deployment, pin
   model revisions (commit hashes) so a changed upstream model cannot change results or
   behaviour silently.
4. **Rate limits are per process and in memory.** With several API workers or servers,
   use a shared store (e.g. Redis).
5. **Data at rest is not encrypted** by the application (use disk or volume encryption).
6. **Uploaded documents may be confidential.** With `LLM_PROVIDER=openai_compatible`
   pointing to a hosted API, passages are sent to that provider; use local models for
   confidential material.
