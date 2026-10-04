# 2. Literature Review

> All references were checked against the original publications on 2026-10-04 (see
> references.md). Add patent-specific works the guide recommends.

## 2.1 Retrieval-augmented generation
Lewis et al. [1] introduced retrieval-augmented generation (RAG): a generator conditioned
on passages retrieved from an external corpus, which grounds outputs in evidence and
allows the knowledge source to be updated without retraining. Gao et al. [2] survey the
evolution from "naive" retrieve-then-read pipelines to modular and adaptive RAG, where
retrieval decisions depend on the query. Our baseline corresponds to naive RAG; our agent
belongs to the adaptive family.

## 2.2 Retrieval components
Dense retrieval embeds queries and passages in a shared vector space. BGE-M3 [3] provides
multilingual dense embeddings for passages up to 8,192 tokens and is used here.
Approximate nearest-neighbour search over embeddings commonly uses HNSW graphs [4], as
implemented by pgvector. Lexical and dense rankings are complementary; Reciprocal Rank
Fusion (RRF) [5] combines ranked lists without score calibration and is used for our
hybrid search. Cross-encoder rerankers [6] rescore a candidate list by reading query
and passage jointly and are evaluated as an option (Experiment D).

## 2.3 LLM agents and tool use
ReAct [7] interleaves reasoning steps with tool calls, letting a model decide which
information to gather. Self-RAG [8] lets a model decide when to retrieve and critique its
own output. Our agent follows a more constrained design: an explicit state machine
(LangGraph) in which a planner (rules or LLM) selects among typed tools, which keeps
behaviour inspectable and allows tool selection to be evaluated against labels.

## 2.4 Hallucination and its detection
Ji et al. [9] survey hallucination in natural language generation, distinguishing
content unsupported by the source (intrinsic/extrinsic). Detection approaches include
sampling consistency (SelfCheckGPT [10]), decomposition into atomic facts checked against
a knowledge source (FActScore [11]), and NLI-based consistency checking. SummaC [12]
showed that NLI models applied at sentence granularity, with aggregation over premise
sentences, detect inconsistencies far better than document-level NLI, a finding we
reproduced for patent passages. Our verifier uses an NLI cross-encoder built on DeBERTa-v3 [23],
the successor of DeBERTa [13], fine-tuned on the SNLI [24] and MultiNLI [14] corpora.

## 2.5 Citations and evaluation of RAG
Gao et al. [15] (ALCE) evaluate whether generated text is supported by its citations,
measuring citation recall and precision. RAGAS [16] proposes reference-free RAG metrics
(faithfulness, answer relevance, context relevance) computed with LLM judges. We adopt
claim-level faithfulness ("grounding") and add misattribution, and we measure the
verifier itself against labelled statements (Experiment I).

## 2.6 Patent retrieval and analysis
Patent retrieval differs from web search: long documents, formal claim language and
recall-oriented tasks such as prior-art search. Shalaby and Zadrozny [17] review patent
retrieval methods, and Krestel et al. [18] survey deep learning for patent analysis.
Unlike these task-specific systems, our work combines retrieval with LLM generation and
statement-level verification for question answering over patents.

## 2.7 Research gap
Existing RAG systems rarely (i) exploit patent structure (claims as units), (ii) select
sources and tools per question while (iii) verifying each generated statement against
its specific citation and detecting misattribution, and (iv) report results with
confidence intervals against a conventional baseline on labelled patent questions, and
(v) test on patents published after the language model's training data, where only live
retrieval can give a correct answer. This project addresses that combination.
