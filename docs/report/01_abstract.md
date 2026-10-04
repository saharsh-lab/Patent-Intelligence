# Abstract

Large language models (LLMs) write fluent statements about patents that no source supports
("hallucinations"), which is unacceptable where one wrong technical detail changes a
claim's meaning. This project presents an **agentic retrieval-augmented generation (RAG)
system for patent intelligence** that answers only from retrieved patent text, cites every
statement and verifies each one against its evidence.

Uploaded documents and live records from the EPO Open Patent Services are split into
claim-aware passages and indexed in PostgreSQL/pgvector with BGE-M3 embeddings and hybrid
retrieval. A LangGraph agent selects tools per question (local search, direct claim
retrieval, live patent import, balanced comparison) and answers with a local LLM
(Qwen3-8B); an NLI verifier labels every statement, flags misattributed citations and
triggers regeneration when grounding is low.

On a frozen test set of 53 questions over 16 real patents, the agent outperformed a
conventional RAG baseline in passage recall@5 (39.4% → 51.1%) and grounding (66.4% →
72.6%), with fewer unsupported statements (22.2% → 17.2%; all 95% intervals excluding
zero), at about twice the latency. On 30 questions about patents published in 2026, after
the LLM's training data, the LLM alone never admitted ignorance and 73% of its statements
were unsupported, while the agent with live EPO access retrieved the asked claim every
time; this experiment also exposed, and led to the fix of, a misattribution bug. Against
150 statements labelled by one team member with AI assistance, the NLI verifier proved
strict (κ 0.16), so grounding scores are conservative. The test labels were AI-written and
not human-verified; both limitations are reported. The system describes technical
similarity only and gives no legal opinions.

**Keywords:** retrieval-augmented generation, LLM agents, hallucination detection,
natural language inference, patent analysis, information retrieval
