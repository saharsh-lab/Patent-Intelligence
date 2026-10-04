# 5. Evaluation Methodology

## 5.1 Research questions
- **RQ1.** Does an agent that selects tools and sources produce better-grounded and more
  accurate answers than a fixed retrieve-then-generate pipeline, and at what cost?
- **RQ2.** How much does claim-level verification with regeneration reduce unsupported
  statements?
- **RQ3.** Which retrieval design choices (chunking, number of passages, reranking)
  matter for patent text?
- **RQ4.** How accurately does an automatic verifier agree with human judgement?
- **RQ5.** Does live patent data matter for patents the LLM cannot know (published after
  its training data)?

## 5.2 Corpus and dataset
The corpus is 16 public patents in three technical domains (wireless-charging
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

The questions used for tuning (dev set `real_v1`, 54 questions) are separate from the
questions used for reporting (test set `real_test_v1`, 53 questions), which use different
facts and were frozen before any system run on them (dataset SHA-256 recorded in each
result). **Who wrote the labels.** Both sets were written by an AI coding assistant from
the patent texts. After the final runs, the same assistant audited every test item
against the patent text (labels re-matched to the corpus, key facts confirmed next to
their passages, generic questions searched across all 16 patents for missing answer
passages, unanswerable questions searched for any answer); this corrected 4 key facts and
changed no question. The stored runs were then re-scored without regenerating answers.
The labels were **not verified by humans**, so retrieval metrics and key-fact recall carry
that limitation; grounding, latency, token and tool metrics do not depend on them.

**Live question set (Experiment E).** A second question set is generated, not written:
EPO is searched for EP and WO publications from 2026 in the three domains, and for each of
15 patents (published 2026-04-15 to 2026-09-30) two questions ask what claim 1 covers and
what one dependent claim adds. The ground truth is the claim text and abstract as EPO
supplied them, frozen in the question set before any run
(`experiments/datasets/live_epo_v1/`). Answers are scored by the share of the claim's
content words they contain ("claim content") and by the NLI verifier against the real
claims and abstract ("supported by the patent"); no human labels are involved.

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
| E | Live EPO access vs. local documents only vs. the LLM alone, on 2026 patents | LLM, question set |
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
