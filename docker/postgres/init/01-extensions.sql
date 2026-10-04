-- Runs automatically the first time the database container starts.
-- Enables pgvector in the main database and creates a separate test database
-- so automated tests never touch your real data.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE DATABASE patent_rag_test;
\connect patent_rag_test
CREATE EXTENSION IF NOT EXISTS vector;

-- Experiments (Phase 9) get their own database, because the evaluation runner
-- deletes and re-ingests its corpus between variants.
\connect patent_rag
CREATE DATABASE patent_rag_eval;
\connect patent_rag_eval
CREATE EXTENSION IF NOT EXISTS vector;

-- User accounts (added after Phase 12) live in their own database
\connect patent_rag
CREATE DATABASE patent_rag_auth;
CREATE DATABASE patent_rag_auth_test;
