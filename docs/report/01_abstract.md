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

An evaluation framework with a frozen test set of 53 questions over 16 real patents,
content-based relevance labels, and paired bootstrap confidence intervals compares the
agent with a conventional RAG baseline and isolates the effect of chunking, retrieval
depth, reranking, tool selection, planner type and verification. Compared with the
baseline, the agent raised passage recall@5 from 39.4% to 51.1% and the grounding score
(answer statements verified against their evidence, partial support counting half) from
66.4% to 72.6%, and lowered unsupported statements
from 22.2% to 17.2% (all differences with 95% intervals excluding zero), at about twice
the latency. Regenerating poorly grounded answers added a further 4.0 points of grounding,
and claim-aware chunking was essential for verifiable answers (grounding 65.3% vs. 48.0%
with fixed-size windows). On 30 questions about patents published in 2026, after the LLM's
training data, the LLM alone never admitted ignorance and 73% of its statements were
unsupported by the patent, whereas the agent with live EPO access retrieved the asked
claim every time. On 150 answer statements labelled by one team
member with AI assistance, the NLI verifier caught 5 of 9 unsupported statements but
flagged 30% of supported ones (Cohen's κ 0.16), so its grounding scores are conservative.
The test labels were written and audited by an AI assistant and not verified by humans;
this and the single, AI-assisted annotator are stated as limitations. The system describes technical similarity
only and does not provide legal opinions on validity or infringement.

**Keywords:** retrieval-augmented generation, LLM agents, hallucination detection,
natural language inference, patent analysis, information retrieval
