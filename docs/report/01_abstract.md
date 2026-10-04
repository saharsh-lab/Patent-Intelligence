# Abstract

Patent professionals and engineers increasingly use large language models (LLMs) to
read and compare patents, but LLMs produce fluent statements that are not supported
by any source ("hallucinations"), which is unacceptable in a domain where a single
wrong technical detail changes the meaning of a claim. This project presents an
**agentic retrieval-augmented generation (RAG) system for patent intelligence** that
answers questions only from retrieved patent text, cites every statement, and
verifies each statement against its cited evidence.

The system ingests patent documents (uploaded PDF/DOCX/TXT files and live records from
the EPO Open Patent Services), segments them into patent-aware passages (one per claim),
and indexes them in PostgreSQL with pgvector using BGE-M3 embeddings and hybrid
(semantic + keyword) retrieval with Reciprocal Rank Fusion. A LangGraph agent classifies
each question, selects tools (local search, direct claim retrieval, external patent
search, balanced multi-patent comparison), and generates a cited answer with a locally
hosted LLM (Qwen3-8B). A claim-level verifier based on natural language inference (NLI)
labels every answer statement as supported, partially supported or unsupported, detects
statements attributed to the wrong source, and triggers evidence-augmented regeneration
when grounding is low.

An evaluation framework with a labelled question set over [RESULT: N] real patents,
content-based relevance labels, and bootstrap confidence intervals compares the agent
with a conventional RAG baseline and isolates the effect of chunking, retrieval depth,
reranking, tool selection, planner type and verification. [RESULT: one or two sentences
with the main findings, e.g. grounding score baseline vs. agent with 95% CI, verifier
agreement with human labels (Cohen's κ).] The system describes technical similarity only
and does not provide legal opinions on validity or infringement.

**Keywords:** retrieval-augmented generation, LLM agents, hallucination detection,
natural language inference, patent analysis, information retrieval
