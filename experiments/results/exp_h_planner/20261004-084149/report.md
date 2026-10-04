# exp_h_planner — 20261004-084149

Rules planner vs. LLM planner (Experiment H).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 40 (0 failed).

> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **rules** (agentic): `agent_planner=rules`
- **llm** (agentic): `agent_planner=llm`

## Results (mean [95% CI], n questions)

| Metric | rules | llm |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 24.7% [20.0%, 30.6%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 86.3% [76.4%, 97.1%] (n=17) |
| MRR | 0.749 [0.581, 0.909] (n=17) | 0.749 [0.581, 0.909] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 23.9% [18.8%, 29.8%] (n=17) | 23.9% [18.8%, 29.8%] (n=17) |
| Context recall | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) |
| Answer/abstain correct | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 94.4% [87.4%, 100.0%] (n=17) | 94.4% [87.4%, 100.0%] (n=17) |
| Invalid citations | 0 [0, 0] (n=17) | 0 [0, 0] (n=17) |
| Grounding score | 84.1% [71.2%, 94.6%] (n=17) | 84.1% [71.2%, 94.6%] (n=17) |
| Unsupported-claim rate | 9.1% [0.0%, 22.0%] (n=17) | 9.1% [0.0%, 22.0%] (n=17) |
| Misattribution rate | 7.4% [1.5%, 14.2%] (n=17) | 7.4% [1.5%, 14.2%] (n=17) |
| Regenerated | 23.5% [5.9%, 47.1%] (n=17) | 23.5% [5.9%, 47.1%] (n=17) |
| Regeneration gain | 0.198 [0.062, 0.323] (n=4) | 0.198 [0.062, 0.323] (n=4) |
| **Comparison** | | |
| Table cells cited | 100.0% [100.0%, 100.0%] (n=2) | 100.0% [100.0%, 100.0%] (n=2) |
| Cross-source citations | 0 [0, 0] (n=2) | 0 [0, 0] (n=2) |
| **Agent** | | |
| Intent accuracy | 100.0% [100.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| Tool precision | 100.0% [100.0%, 100.0%] (n=20) | 96.2% [88.8%, 100.0%] (n=20) |
| Tool recall | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| Tool set exact | 100.0% [100.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| Legal question flagged | 100.0% (n=1) | 100.0% (n=1) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 7,995 ms [4,812 ms, 11,810 ms] (n=20) | 9,637 ms [6,431 ms, 13,458 ms] (n=20) |
| LLM calls | 1.2 [1.1, 1.4] (n=20) | 2.2 [2.0, 2.4] (n=20) |
| Tokens | 1,124.1 [956.7, 1,311.9] (n=20) | 1,405.2 [1,219.5, 1,603.2] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- rules: p50 4,352 ms, p95 26,839 ms
- llm: p50 5,694 ms, p95 28,711 ms

## Paired differences vs. rules

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| llm | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | MRR | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Context precision | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Context recall | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| llm | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| llm | Citation coverage | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Invalid citations | 0 [0, 0] | 0/0/17 | no |
| llm | Grounding score | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Unsupported-claim rate | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Misattribution rate | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Regenerated | 0.000 [0.000, 0.000] | 0/0/17 | no |
| llm | Regeneration gain | 0.000 [0.000, 0.000] | 0/0/4 | no |
| llm | Table cells cited | 0.000 [0.000, 0.000] | 0/0/2 | no |
| llm | Cross-source citations | 0 [0, 0] | 0/0/2 | no |
| llm | Intent accuracy | -0.050 [-0.150, 0.000] | 0/1/19 | no |
| llm | Tool precision | -0.037 [-0.113, 0.000] | 0/1/19 | no |
| llm | Tool recall | 0.000 [0.000, 0.000] | 0/0/20 | no |
| llm | Tool set exact | -0.050 [-0.150, 0.000] | 0/1/19 | no |
| llm | Legal question flagged | 0.000 | 0/0/1 | no |
| llm | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| llm | Latency | 1,642 ms [1,167 ms, 2,043 ms] | 18/2/0 | yes |
| llm | LLM calls | 1 [1, 1] | 20/0/0 | yes |
| llm | Tokens | 281.1 [227, 309.4] | 19/1/0 | yes |
| llm | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
