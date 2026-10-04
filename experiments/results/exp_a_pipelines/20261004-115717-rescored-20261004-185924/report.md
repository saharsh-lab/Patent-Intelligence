# exp_a_pipelines — 20261004-115717-rescored-20261004-185924

Baseline RAG vs. agentic RAG (Experiment A).

Dataset **real_test_v1** (53 questions, labelled by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified), 1 repeat(s), k = 5. Runs: 106 (0 failed).

> **Note:** Rescored from run 20261004-115717 with the current labels and scoring code (the answers themselves were not regenerated).
> **Note:** Limitation: labels by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified. State this wherever these numbers are reported.

## Variants

- **baseline** (baseline): defaults
- **agentic** (agentic): defaults

## Results (mean [95% CI], n questions)

| Metric | baseline | agentic |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 8.9% [6.0%, 11.9%] (n=47) | 11.9% [8.9%, 14.9%] (n=47) |
| Recall@k | 39.4% [26.6%, 53.2%] (n=47) | 51.1% [37.2%, 63.8%] (n=47) |
| MRR | 0.257 [0.160, 0.358] (n=47) | 0.455 [0.328, 0.578] (n=47) |
| Hit@k | 42.6% [27.7%, 57.4%] (n=47) | 57.4% [42.6%, 70.2%] (n=47) |
| Context precision | 7.4% [5.0%, 9.9%] (n=47) | 10.8% [8.3%, 13.3%] (n=47) |
| Context recall | 39.4% [26.6%, 53.2%] (n=47) | 58.5% [44.7%, 71.3%] (n=47) |
| Right sources found | 95.7% [90.4%, 100.0%] (n=47) | 97.9% [93.6%, 100.0%] (n=47) |
| Passages from right sources | 74.8% [65.2%, 83.7%] (n=47) | 80.5% [71.7%, 88.1%] (n=47) |
| **Answer** | | |
| Key-fact recall | 68.1% [52.8%, 83.3%] (n=36) | 69.7% [55.3%, 82.9%] (n=38) |
| Answer/abstain correct | 90.6% [83.0%, 98.1%] (n=53) | 96.2% [90.6%, 100.0%] (n=53) |
| **Grounding** | | |
| Citation coverage | 82.0% [74.8%, 88.5%] (n=44) | 92.3% [86.6%, 96.8%] (n=47) |
| Invalid citations | 0 [0, 0] (n=44) | 0.1 [0, 0.3] (n=47) |
| Grounding score | 66.4% [57.1%, 75.3%] (n=44) | 72.6% [64.5%, 79.9%] (n=47) |
| Unsupported-claim rate | 22.2% [13.6%, 31.5%] (n=44) | 17.2% [10.2%, 25.7%] (n=47) |
| Misattribution rate | 13.7% [7.8%, 20.8%] (n=44) | 12.9% [7.2%, 19.6%] (n=47) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=44) | 44.7% [29.8%, 59.6%] (n=47) |
| Regeneration gain | – | 0.092 [0.036, 0.155] (n=21) |
| **Comparison** | | |
| Table cells cited | – | 100.0% [100.0%, 100.0%] (n=7) |
| Cross-source citations | – | 0 [0, 0] (n=7) |
| **Agent** | | |
| Intent accuracy | – | 92.5% [84.9%, 98.1%] (n=53) |
| Tool precision | – | 100.0% [100.0%, 100.0%] (n=53) |
| Tool recall | – | 100.0% [100.0%, 100.0%] (n=53) |
| Tool set exact | – | 100.0% [100.0%, 100.0%] (n=53) |
| Legal question flagged | – | 100.0% [100.0%, 100.0%] (n=3) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 14,662 ms [12,728 ms, 16,591 ms] (n=53) | 28,647 ms [24,466 ms, 33,080 ms] (n=53) |
| LLM calls | 1 [1, 1] (n=53) | 2.4 [2.3, 2.5] (n=53) |
| Tokens | 2,474.5 [2,349.7, 2,597.6] (n=53) | 4,024.9 [3,610.0, 4,469.4] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- baseline: p50 13,250 ms, p95 26,833 ms
- agentic: p50 29,296 ms, p95 53,835 ms

## Paired differences vs. baseline

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| agentic | Precision@k | 0.030 [0.013, 0.051] | 7/0/40 | yes |
| agentic | Recall@k | 0.117 [0.043, 0.202] | 7/0/40 | yes |
| agentic | MRR | 0.198 [0.112, 0.295] | 17/1/29 | yes |
| agentic | Hit@k | 0.149 [0.064, 0.255] | 7/0/40 | yes |
| agentic | Context precision | 0.033 [0.015, 0.055] | 11/2/34 | yes |
| agentic | Context recall | 0.191 [0.096, 0.298] | 11/0/36 | yes |
| agentic | Right sources found | 0.021 [0.000, 0.053] | 2/0/45 | no |
| agentic | Passages from right sources | 0.057 [0.008, 0.125] | 7/1/39 | yes |
| agentic | Key-fact recall | 0.000 [-0.111, 0.111] | 2/2/32 | no |
| agentic | Answer/abstain correct | 0.057 [0.000, 0.132] | 3/0/50 | no |
| agentic | Citation coverage | 0.115 [0.050, 0.185] | 13/3/28 | yes |
| agentic | Invalid citations | 0 [0, 0] | 0/0/44 | no |
| agentic | Grounding score | 0.064 [0.007, 0.124] | 13/4/27 | yes |
| agentic | Unsupported-claim rate | -0.050 [-0.107, -0.000] | 5/9/30 | yes |
| agentic | Misattribution rate | -0.013 [-0.050, 0.026] | 3/7/34 | no |
| agentic | Regenerated | 0.432 [0.295, 0.568] | 19/0/25 | yes |
| agentic | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| agentic | Latency | 13,985 ms [10,344 ms, 17,886 ms] | 43/10/0 | yes |
| agentic | LLM calls | 1.4 [1.3, 1.5] | 53/0/0 | yes |
| agentic | Tokens | 1,550.4 [1,175.7, 1,951.1] | 52/1/0 | yes |
| agentic | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
