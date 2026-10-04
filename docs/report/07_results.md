# 6. Results

> **Template.** Fill each table with the generated output for the final test-set run:
> `cd backend && .venv/bin/python -m app.evaluation tables --result ../experiments/results/<exp>/<run> --format latex`
> Do not type numbers by hand. Do not use results whose report carries a "synthetic",
> "dev" or "Draft labels" warning. Name the result folder of every table in an appendix.

## 6.1 Experiment A: baseline vs. agentic RAG (RQ1)
[TABLE: tables --result <exp_a test run>]

Describe: retrieval at document and passage level; key-fact recall; answer/abstain
accuracy; grounding and unsupported rate; latency and tokens. State which differences are
clear (†) and which are not. Break down by question type (summary.json → by_type) if the
types behave differently, e.g. claim questions (direct section retrieval) vs. lookups.

## 6.2 Experiment G: verification and regeneration (RQ2)
[TABLE: tables --result <exp_g run> --metrics grounding_score,unsupported_rate,regenerated,regeneration_gain,key_fact_recall,latency_ms,total_tokens]

## 6.3 Experiments B, C, D: retrieval design (RQ3)
[TABLE per experiment]. For B, report context tokens next to recall (bigger chunks are
"relevant" more easily).

## 6.4 Experiments F and H: tool selection and planner
[TABLES]. Report intent accuracy and tool precision/recall with the cost difference.

## 6.5 Experiment I: verifier accuracy (RQ4)
[TABLE from experiments/results/exp_i_verifiers/<run>/report.md: accuracy, κ, detection
P/R/F1 per method] together with the agreement between the two human labellers (κ). The
human–human κ is the ceiling.

## 6.6 Experiment S: invention-analysis self-check
Each of the 16 test-corpus patents had its first independent claim analysed as if it
were a new invention, with the patent itself in the index (run
`experiments/results/selfcheck_invention/20261004-175038`; Qwen3-8B, BGE-M3, NLI verifier).
This experiment needs no human labels: the right answer (the patent itself) is known, and
the technical domain of each patent comes from the search topic used to build the corpus.

| Metric | Mean [95% CI] | n |
|---|---|---|
| Own patent ranked first | 1.000 [1.000, 1.000] | 16 |
| Own claim features marked disclosed | 1.000 [1.000, 1.000] | 16 |
| Closest other document from the same domain | 1.000 [1.000, 1.000] | 16 |
| Top-3 other documents from the same domain | 0.927 [0.844, 1.000] | 16 |
| Latency per analysis | 7.7 s [5.9 s, 9.7 s] | 16 |

Every patent found itself first with all of its claim features marked disclosed, and with
itself excluded, the closest remaining document always came from the same technical
domain. **What this does and does not show:** the query is the patent's own claim, so the
wording overlaps exactly; this tests that the pipeline (feature extraction, ranking,
verification of 16 × up to 40 cells) works end to end at scale, not how well it handles a
user's own description. When every case succeeds, the bootstrap interval collapses to
[1, 1] and understates the uncertainty: by the "rule of three", 16 successes out of 16
are still consistent with a true success rate as low as about 81% (95% confidence).
There were no failures to analyse. One engineering finding: the first run skipped a continuation patent
whose claims 1–14 were cancelled; the self-check now uses the first independent claim.

## 6.7 Qualitative examples
Pick two or three runs (a chat, the Research console, or the eval database by run id): one well-grounded
answer, one with a detected unsupported or misattributed statement, one regeneration.

## 6.8 Engineering findings during development
These are observations from building and testing the system (docs/observations.md), not
measured results on the test set; they may be reported as such:
- A small NLI model loses entailment when the premise has extra sentences (p = 0.99 for
  the sentence alone vs. 0.04–0.38 within its paragraph); sentence-window scoring fixes it.
- Matching relevance on chunk metadata biased the chunking comparison against fixed-size
  chunks; content anchors removed the bias.
- Latency comparisons were confounded by run order and by the LLM server's prompt cache;
  interleaving, counterbalancing and warm-up address this.
- On real patents an LLM planner sent plain lookups to similar-patent search, causing
  wrong abstentions; output validation against the question text prevents it.
