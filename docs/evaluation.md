# Evaluation

> Status (Phase 9): every metric marked ✅ below is computed by `app/evaluation/` for each
> run and aggregated with 95% bootstrap CIs. **No research results yet**: the dev dataset
> is synthetic. Formulas: `app/evaluation/metrics.py`; per-run scoring:
> `app/evaluation/scoring.py`.

## Metrics

✅ = computed per run by `scoring.py` and aggregated in every result. ⏳ = not yet.

| Group | Metric | Definition | Ground truth | |
|---|---|---|---|---|
| Retrieval | Precision@k | relevant passages in top k ÷ k | relevant passages | ✅ |
| Retrieval | Recall@k | labels found in top k ÷ all labels | relevant passages | ✅ |
| Retrieval | MRR | 1 ÷ rank of first relevant passage | relevant passages | ✅ |
| Retrieval | Hit@k | any relevant passage in top k | relevant passages | ✅ |
| Retrieval | Context precision / recall | as above, over every passage given to the LLM | relevant passages | ✅ |
| Retrieval | Similar-patent ranking quality | precision@k of ranked candidates vs. labelled patents | relevant patents | ⏳ (needs EPO) |
| Answer | Key-fact recall | labelled facts present in the answer ÷ all facts | key facts | ✅ |
| Answer | Answer/abstain correct | answered an answerable question, or abstained on an unanswerable one | answerable flag | ✅ |
| Answer | Answer relevance | judge score: does the answer address the question? | — | ⏳ |
| Grounding | Grounding score (faithfulness) | (supported + 0.5 × partial) ÷ checked statements | — | ✅ |
| Grounding | Unsupported-claim rate | unsupported ÷ checked statements | — | ✅ |
| Grounding | Misattribution rate | statements supported only by an uncited passage ÷ checked | — | ✅ |
| Grounding | Citation coverage | cited sentences ÷ answer sentences | — | ✅ |
| Grounding | Invalid (fabricated) citations | citation labels that were never supplied | — | ✅ |
| Grounding | Regeneration rate / gain | share regenerated; grounding(final) − grounding(first) | — | ✅ |
| Grounding | Verifier accuracy, κ, detection P/R/F1 | verifier verdicts vs. human verdicts (Experiment I) | human verdicts | ✅ |
| Comparison | Table cells cited | filled cells citing their own source ÷ filled cells | — | ✅ |
| Comparison | Cross-source citations | cell citations pointing at another source's passage | — | ✅ |
| Agent | Intent accuracy | planner intent = expected intent | expected intent | ✅ |
| Agent | Tool precision / recall / exact set | expected tools used ÷ used; ÷ expected; sets equal | expected tools | ✅ |
| Agent | Legal question flagged | legal flag = label | legal flag | ✅ |
| Agent | Task success rate | human judgement of the whole answer | human | ⏳ |
| System | Run failure rate | failed runs ÷ runs | — | ✅ |
| System | Latency (mean, p50, p95) | `agent_runs.latency_ms` | — | ✅ |
| System | LLM calls, tokens, cost | `agent_runs` usage (cost from configured prices) | — | ✅ |

Notes:

- With a single relevant passage, precision@k cannot exceed 1/k; prefer recall@k, MRR and
  hit@k for single-fact questions.
- A metric that does not apply to a run (retrieval for unanswerable questions, grounding
  for abstentions, agent metrics for the baseline) is left out of that average, and every
  table shows *n*.
- `threshold_sweep` in `summary.json` shows, for each similarity threshold, how often the
  answer/abstain decision would match the labels. It is used to calibrate
  `RETRIEVAL_MIN_SIMILARITY`, and it approximates the gate (it ignores the gate's
  keyword path).

## Where each number comes from

- Retrieval metrics: the run's stored evidence (`agent_runs.answer.evidence`, a copy of
  each passage at retrieval time) matched against the dataset's content-based labels.
- Faithfulness / grounding: `claim_verifications`.
- Agent metrics: `tool_calls` vs. the dataset's expected tools.
- System metrics: `agent_runs`.

## Validity notes

- LLM-as-judge scores will be checked against a human-labelled sample before use.
- Results are reported with the number of questions and, where possible, confidence
  intervals; small differences on small datasets are not claimed as significant.
