# exp_a_pipelines — 20261004-012821

Baseline RAG vs. agentic RAG (Experiment A).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 40 (0 failed).

> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **baseline** (baseline): defaults
- **agentic** (agentic): defaults

## Results (mean [95% CI], n questions)

| Metric | baseline | agentic |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 22.4% [16.5%, 29.4%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 77.5% [60.8%, 92.2%] (n=17) |
| MRR | 0.742 [0.592, 0.882] (n=17) | 0.762 [0.574, 0.941] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 88.2% [70.6%, 100.0%] (n=17) |
| Context precision | 23.5% [18.6%, 29.4%] (n=17) | 21.0% [14.9%, 27.8%] (n=17) |
| Context recall | 94.1% [85.3%, 100.0%] (n=17) | 88.2% [70.6%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 92.9% [78.6%, 100.0%] (n=14) |
| Answer/abstain correct | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 92.3% [84.5%, 98.4%] (n=16) | 95.6% [88.1%, 100.0%] (n=16) |
| Invalid citations | 0 [0, 0] (n=16) | 0 [0, 0] (n=16) |
| Grounding score | 76.7% [61.0%, 90.3%] (n=16) | 70.8% [53.7%, 85.5%] (n=16) |
| Unsupported-claim rate | 16.4% [5.1%, 30.6%] (n=16) | 22.7% [8.3%, 39.9%] (n=16) |
| Misattribution rate | 7.7% [1.6%, 15.5%] (n=16) | 6.2% [1.0%, 14.1%] (n=16) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=16) | 43.8% [18.8%, 68.8%] (n=16) |
| Regeneration gain | – | 0.151 [0.036, 0.294] (n=7) |
| **Comparison** | | |
| Table cells cited | – | 100.0% [100.0%, 100.0%] (n=2) |
| Cross-source citations | – | 0 [0, 0] (n=2) |
| **Agent** | | |
| Intent accuracy | – | 90.0% [75.0%, 100.0%] (n=20) |
| Tool precision | – | 56.2% [35.0%, 76.2%] (n=20) |
| Tool recall | – | 60.0% [40.0%, 80.0%] (n=20) |
| Tool set exact | – | 55.0% [35.0%, 75.0%] (n=20) |
| Legal question flagged | – | 100.0% (n=1) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 5,102 ms [3,754 ms, 6,521 ms] (n=20) | 11,971 ms [8,049 ms, 16,410 ms] (n=20) |
| LLM calls | 1 [1, 1] (n=20) | 2.3 [2.0, 2.5] (n=20) |
| Tokens | 861.9 [809, 911.1] (n=20) | 1,488 [1,248.8, 1,722.4] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- baseline: p50 4,293 ms, p95 9,981 ms
- agentic: p50 9,278 ms, p95 32,735 ms

## Paired differences vs. baseline

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| agentic | Precision@k | -0.024 [-0.059, 0.000] | 0/2/15 | no |
| agentic | Recall@k | -0.088 [-0.235, 0.000] | 0/2/15 | no |
| agentic | MRR | 0.020 [-0.227, 0.250] | 4/4/9 | no |
| agentic | Hit@k | -0.118 [-0.294, 0.000] | 0/2/15 | no |
| agentic | Context precision | -0.025 [-0.075, 0.006] | 2/2/13 | no |
| agentic | Context recall | -0.059 [-0.236, 0.118] | 2/2/13 | no |
| agentic | Key-fact recall | 0.000 [-0.214, 0.214] | 1/1/12 | no |
| agentic | Answer/abstain correct | 0.000 [-0.150, 0.150] | 1/1/18 | no |
| agentic | Citation coverage | 0.036 [-0.067, 0.138] | 3/1/11 | no |
| agentic | Invalid citations | 0 [0, 0] | 0/0/15 | no |
| agentic | Grounding score | -0.052 [-0.178, 0.051] | 2/5/8 | no |
| agentic | Unsupported-claim rate | 0.067 [-0.054, 0.233] | 3/1/11 | no |
| agentic | Misattribution rate | -0.021 [-0.119, 0.073] | 2/3/10 | no |
| agentic | Regenerated | 0.467 [0.200, 0.733] | 7/0/8 | yes |
| agentic | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| agentic | Latency | 6,869 ms [3,609 ms, 10,831 ms] | 19/1/0 | yes |
| agentic | LLM calls | 1.3 [1.1, 1.6] | 19/0/1 | yes |
| agentic | Tokens | 626.1 [370.9, 874.7] | 18/2/0 | yes |
| agentic | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
