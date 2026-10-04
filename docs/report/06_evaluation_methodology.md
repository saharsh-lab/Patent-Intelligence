# 5. Evaluation Methodology

## 5.1 Research questions
- **RQ1.** Does an agent that selects tools and sources produce better-grounded and more
  accurate answers than a fixed retrieve-then-generate pipeline, and at what cost?
- **RQ2.** How much does claim-level verification with regeneration reduce unsupported
  statements?
- **RQ3.** Which retrieval design choices (chunking, number of passages, reranking)
  matter for patent text?
- **RQ4.** How accurately does an automatic verifier agree with human judgement?

## 5.2 Corpus and dataset
The corpus is [RESULT: N] public patents in three technical domains (wireless-charging
foreign object detection, electric-vehicle battery thermal management, immersion
cooling), including near-neighbour documents so retrieval must discriminate. Patents were
downloaded as text with standard section headings (backend/scripts/build_corpus.py).

Questions cover eight types: single-fact lookups, multi-passage questions, claim
explanations (document selected), questions naming a publication number, comparisons of
two selected documents, unanswerable questions (the correct behaviour is to abstain), and
legal-opinion questions (the correct behaviour is to decline the legal opinion and give a
technical comparison). Each question is labelled with:
- relevant passages, identified by **content** (document + short quote, claim number or
  section), never by chunk ID, so the same labels score any chunking strategy;
- key facts a correct answer must contain;
- expected intent and expected tools;
- whether it is answerable and whether it asks for a legal opinion.

Labels were drafted, then checked by two team members [RESULT: agreement statistics];
disagreements were resolved by discussion. The questions used for tuning (dev set,
[RESULT: n]) are separate from the questions used for reporting (test set, [RESULT: n]),
which were written independently and frozen before any run (dataset SHA-256 recorded in
each result).

## 5.3 Metrics
| Group | Metric | Definition |
|---|---|---|
| Retrieval | Right sources found | labelled documents represented in the evidence ÷ labelled documents |
| Retrieval | Recall@k, MRR, Hit@k | passage-level, against content labels (k = 5) |
| Answer | Key-fact recall | labelled facts present in the answer ÷ facts |
| Answer | Answer/abstain accuracy | answered answerable / abstained on unanswerable |
| Grounding | Grounding score | (supported + ½ partial) ÷ checked statements |
| Grounding | Unsupported / misattributed rate | share of statements |
| Grounding | Citation coverage, invalid citations | cited sentences ÷ sentences; labels not supplied |
| Agent | Intent accuracy, tool precision/recall | against expected intent and tools |
| Cost | Latency (mean, median, p95), LLM calls, tokens | per question |
| Verifier | Accuracy, Cohen's κ, detection P/R/F1 | verifier verdicts vs. human verdicts |

Passage-level retrieval metrics underestimate retrieval quality when labels list only some
of the passages that answer a question (patents repeat facts across sections), so
document-level metrics are reported next to them.

## 5.4 Experiments
| ID | Compares | Held constant |
|---|---|---|
| A | Baseline RAG vs. agentic RAG | LLM, embeddings, corpus |
| B | Section-aware vs. fixed-size chunking | Retrieval, LLM |
| C | Passages given to the LLM (k = 3, 6, 10) | Everything else |
| D | Without vs. with cross-encoder reranking | Candidate pool (30) |
| E | Single source vs. multiple sources | Agent (requires EPO access) |
| F | Tool selection vs. running every available tool | Tools available |
| G | No verification vs. verification vs. verification + regeneration | Retrieval |
| H | Rule-based vs. LLM planner | Everything else |
| I | Verifier methods (NLI, LLM judge, lexical) vs. human labels | Statements judged |
| S | Invention-analysis self-check (label-free) | Corpus |

**Experiment S (self-check).** For every patent in the corpus its own claim 1 is used as the
invention description. *Included:* the patent should be ranked first and its claim features
marked as disclosed in it (tests retrieval and the verifier with a known answer).
*Excluded:* with the patent hidden, the closest documents should belong to the same technical
domain (same-domain@1, @3). No human labels are required, so the check scales to any corpus;
because queries share wording with their source, it is easier than real use and complements
the labelled test set.

## 5.5 Procedure and statistics
All variants run on the same questions with temperature 0, through the same code as the
application, against a separate database containing only the corpus. Variants sharing an
index are run interleaved per question with the starting variant rotated
(counterbalancing), after one untimed warm-up question, on an otherwise idle machine.
Repeats are averaged per question; questions are the unit of analysis. Means are reported
with 95% percentile-bootstrap confidence intervals (2,000 resamples, fixed seed), and
variants are compared with paired bootstrap differences; a difference is reported as such
only when its 95% interval excludes zero. Every result folder stores the configuration,
all settings, package versions and the dataset fingerprint.
