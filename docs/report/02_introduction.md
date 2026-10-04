# 1. Introduction

## 1.1 Background
Patents are long, formally written technical documents. A single patent typically has an
abstract, a background, a summary, a detailed description with numbered paragraphs, and
a set of claims that define what is protected. Engineers checking prior art, students
studying a technology, and analysts comparing competitors must read many such documents
and extract precise technical facts: which components a claim requires, what a dependent
claim adds, how two inventions differ.

Large language models can summarise and answer questions about text, but when they
answer from their parametric memory they may produce statements that no source supports.
In patent work such errors are costly: attributing a feature to the wrong patent, or
inventing a numeric limit, changes the technical meaning entirely.

## 1.2 Problem statement
Design and evaluate a system that answers technical questions about patents such that
(i) every statement is derived from and cited to retrieved patent text, (ii) unsupported
statements are detected automatically, and (iii) the choice of retrieval steps adapts to
the question (single fact, specific claim, comparison of several patents, search for
similar patents), using live patent data where needed.

## 1.3 Objectives
1. Ingest patents from uploads and from a live patent database, preserving patent
   structure (sections and individual claims).
2. Retrieve relevant evidence with hybrid semantic and keyword search.
3. Build an agent that selects tools and sources per question and recovers from failures.
4. Generate answers that cite evidence for every statement and separate interpretation
   from fact.
5. Verify answers at statement level and regenerate low-grounded answers.
6. Evaluate the system against a conventional RAG baseline with a labelled dataset and
   statistically sound comparisons.

## 1.4 Contributions
- A patent-aware ingestion pipeline (section detection, one chunk per claim) with
  content-based relevance labelling that keeps evaluation comparable across chunking
  strategies.
- An agentic RAG pipeline (LangGraph) with seven tools, including direct claim retrieval
  and balanced evidence collection for multi-patent comparison.
- A two-pass, claim-level verifier that detects unsupported and *misattributed*
  statements, using sentence-window NLI, and an evidence-augmented regeneration loop.
- An evaluation framework (dataset format, runner, metrics, bootstrap confidence
  intervals, paired comparisons, verifier-vs-human agreement) and a set of controlled
  experiments (A–I).
- Documented engineering findings on evaluating such systems, e.g. the effect of
  multi-sentence premises on small NLI models and order effects in latency measurement.

## 1.5 Scope and limitations
The system reports **technical** similarity and evidence only; it does not give legal
opinions on novelty, validity or infringement and states this in every relevant answer.
It is a single-user research prototype without user authentication. Experiments use one
locally hosted LLM; results may differ for other models.

## 1.6 Report organisation
Chapter 2 reviews related work. Chapter 3 presents the system design and Chapter 4 the
implementation. Chapter 5 describes the evaluation methodology, Chapter 6 the results,
Chapter 7 discusses them with limitations, and Chapter 8 concludes.
