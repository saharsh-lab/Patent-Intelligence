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
[TABLE from experiments/results/selfcheck_invention/<run>/report.md: own patent ranked first,
own claim features marked disclosed, same-domain@1 and @3, latency]. Discuss failures: which
patents did not find themselves, and why (e.g. claims with generic wording).

## 6.7 Qualitative examples
Pick two or three runs (Ask AI page, or the eval database by run id): one well-grounded
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
