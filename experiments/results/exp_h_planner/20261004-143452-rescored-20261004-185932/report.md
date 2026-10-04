# exp_h_planner — 20261004-143452-rescored-20261004-185932

Rules planner vs. LLM planner (Experiment H).

Dataset **real_test_v1** (53 questions, labelled by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified), 1 repeat(s), k = 5. Runs: 106 (0 failed).

> **Note:** Rescored from run 20261004-143452 with the current labels and scoring code (the answers themselves were not regenerated).
> **Note:** Limitation: labels by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified. State this wherever these numbers are reported.

## Variants

- **rules** (agentic): `agent_planner=rules`
- **llm** (agentic): `agent_planner=llm`

## Results (mean [95% CI], n questions)

| Metric | rules | llm |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 11.9% [8.9%, 14.9%] (n=47) | 11.9% [8.9%, 14.9%] (n=47) |
| Recall@k | 51.1% [37.2%, 63.8%] (n=47) | 51.1% [37.2%, 63.8%] (n=47) |
| MRR | 0.452 [0.326, 0.575] (n=47) | 0.452 [0.326, 0.575] (n=47) |
| Hit@k | 57.4% [42.6%, 70.2%] (n=47) | 57.4% [42.6%, 70.2%] (n=47) |
| Context precision | 10.6% [8.0%, 13.2%] (n=47) | 10.6% [8.0%, 13.2%] (n=47) |
| Context recall | 57.4% [43.6%, 70.2%] (n=47) | 57.4% [43.6%, 70.2%] (n=47) |
| Right sources found | 97.9% [93.6%, 100.0%] (n=47) | 97.9% [93.6%, 100.0%] (n=47) |
| Passages from right sources | 80.7% [71.6%, 88.5%] (n=47) | 80.7% [71.6%, 88.5%] (n=47) |
| **Answer** | | |
| Key-fact recall | 72.4% [57.9%, 85.5%] (n=38) | 72.4% [57.9%, 85.5%] (n=38) |
| Answer/abstain correct | 96.2% [90.6%, 100.0%] (n=53) | 96.2% [90.6%, 100.0%] (n=53) |
| **Grounding** | | |
| Citation coverage | 91.5% [85.4%, 96.4%] (n=47) | 90.6% [84.1%, 95.8%] (n=47) |
| Invalid citations | 0.1 [0, 0.4] (n=47) | 0.1 [0, 0.4] (n=47) |
| Grounding score | 74.1% [65.8%, 81.5%] (n=47) | 73.4% [65.0%, 81.1%] (n=47) |
| Unsupported-claim rate | 15.8% [8.6%, 24.1%] (n=47) | 16.6% [9.3%, 25.3%] (n=47) |
| Misattribution rate | 13.1% [7.5%, 19.7%] (n=47) | 13.1% [7.5%, 19.7%] (n=47) |
| Regenerated | 38.3% [25.5%, 53.2%] (n=47) | 38.3% [25.5%, 53.2%] (n=47) |
| Regeneration gain | 0.101 [0.037, 0.178] (n=18) | 0.101 [0.037, 0.178] (n=18) |
| **Comparison** | | |
| Table cells cited | 100.0% [100.0%, 100.0%] (n=7) | 100.0% [100.0%, 100.0%] (n=7) |
| Cross-source citations | 0 [0, 0] (n=7) | 0 [0, 0] (n=7) |
| **Agent** | | |
| Intent accuracy | 100.0% [100.0%, 100.0%] (n=53) | 92.5% [84.9%, 98.1%] (n=53) |
| Tool precision | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Tool recall | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Tool set exact | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Legal question flagged | 100.0% [100.0%, 100.0%] (n=3) | 100.0% [100.0%, 100.0%] (n=3) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 21,647 ms [17,678 ms, 25,857 ms] (n=53) | 24,207 ms [20,334 ms, 28,285 ms] (n=53) |
| LLM calls | 1.3 [1.2, 1.5] (n=53) | 2.3 [2.2, 2.5] (n=53) |
| Tokens | 3,570.0 [3,154.9, 4,024.2] (n=53) | 3,887.6 [3,467.6, 4,348.4] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- rules: p50 19,984 ms, p95 46,446 ms
- llm: p50 22,394 ms, p95 52,985 ms

## Paired differences vs. rules

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| llm | Precision@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Recall@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | MRR | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Hit@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Context precision | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Context recall | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Right sources found | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Passages from right sources | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/38 | no |
| llm | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/53 | no |
| llm | Citation coverage | -0.009 [-0.027, 0.000] | 0/1/46 | no |
| llm | Invalid citations | 0 [0, 0] | 0/0/47 | no |
| llm | Grounding score | -0.007 [-0.021, 0.000] | 0/1/46 | no |
| llm | Unsupported-claim rate | 0.009 [0.000, 0.027] | 1/0/46 | no |
| llm | Misattribution rate | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Regenerated | 0.000 [0.000, 0.000] | 0/0/47 | no |
| llm | Regeneration gain | 0.000 [0.000, 0.000] | 0/0/18 | no |
| llm | Table cells cited | 0.000 [0.000, 0.000] | 0/0/7 | no |
| llm | Cross-source citations | 0 [0, 0] | 0/0/7 | no |
| llm | Intent accuracy | -0.075 [-0.151, -0.019] | 0/4/49 | yes |
| llm | Tool precision | 0.000 [0.000, 0.000] | 0/0/53 | no |
| llm | Tool recall | 0.000 [0.000, 0.000] | 0/0/53 | no |
| llm | Tool set exact | 0.000 [0.000, 0.000] | 0/0/53 | no |
| llm | Legal question flagged | 0.000 [0.000, 0.000] | 0/0/3 | no |
| llm | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| llm | Latency | 2,560 ms [-1,229 ms, 6,745 ms] | 27/26/0 | no |
| llm | LLM calls | 1 [1, 1] | 53/0/0 | yes |
| llm | Tokens | 317.6 [309.5, 330.7] | 53/0/0 | yes |
| llm | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
