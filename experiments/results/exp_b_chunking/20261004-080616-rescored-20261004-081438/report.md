# exp_b_chunking — 20261004-080616-rescored-20261004-081438

Section-aware vs. fixed-size chunking (Experiment B).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 40 (0 failed).

> **Note:** Rescored from run 20261004-080616 with the current labels and scoring code (the answers themselves were not regenerated).
> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **section_aware** (baseline): `chunking_strategy=section_aware`
- **fixed** (baseline): `chunking_strategy=fixed`

## Results (mean [95% CI], n questions)

| Metric | section_aware | fixed |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 28.2% [23.5%, 34.1%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| MRR | 0.742 [0.592, 0.882] (n=17) | 0.931 [0.833, 1.000] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 23.5% [18.6%, 29.4%] (n=17) | 39.7% [30.0%, 51.2%] (n=17) |
| Context recall | 94.1% [85.3%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 100.0% [100.0%, 100.0%] (n=15) |
| Answer/abstain correct | 95.0% [85.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 92.3% [84.5%, 98.4%] (n=16) | 85.3% [73.5%, 94.1%] (n=17) |
| Invalid citations | 0 [0, 0] (n=16) | 0 [0, 0] (n=17) |
| Grounding score | 76.7% [61.0%, 90.3%] (n=16) | 52.2% [32.3%, 70.6%] (n=17) |
| Unsupported-claim rate | 16.4% [5.1%, 30.6%] (n=16) | 41.2% [22.1%, 61.8%] (n=17) |
| Misattribution rate | 7.7% [1.6%, 15.5%] (n=16) | 7.4% [0.0%, 16.2%] (n=17) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=16) | 0.0% [0.0%, 0.0%] (n=17) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 6,501 ms [5,196 ms, 7,872 ms] (n=20) | 11,519 ms [10,163 ms, 13,011 ms] (n=20) |
| LLM calls | 1 [1, 1] (n=20) | 1 [1, 1] (n=20) |
| Tokens | 861.9 [809, 911.1] (n=20) | 1,793.1 [1,585.1, 1,959.3] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- section_aware: p50 4,936 ms, p95 11,449 ms
- fixed: p50 11,218 ms, p95 16,728 ms

## Paired differences vs. section_aware

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| fixed | Precision@k | 0.035 [-0.035, 0.106] | 4/1/12 | no |
| fixed | Recall@k | 0.137 [0.029, 0.236] | 5/0/12 | yes |
| fixed | MRR | 0.189 [0.020, 0.368] | 6/2/9 | yes |
| fixed | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| fixed | Context precision | 0.162 [0.039, 0.299] | 14/3/0 | yes |
| fixed | Context recall | 0.059 [0.000, 0.147] | 2/0/15 | no |
| fixed | Key-fact recall | 0.067 [0.000, 0.200] | 1/0/14 | no |
| fixed | Answer/abstain correct | 0.050 [0.000, 0.150] | 1/0/19 | no |
| fixed | Citation coverage | -0.048 [-0.147, 0.049] | 1/4/11 | no |
| fixed | Invalid citations | 0 [0, 0] | 0/0/16 | no |
| fixed | Grounding score | -0.228 [-0.445, -0.047] | 3/9/4 | yes |
| fixed | Unsupported-claim rate | 0.242 [0.055, 0.460] | 8/2/6 | yes |
| fixed | Misattribution rate | 0.001 [-0.094, 0.100] | 3/2/11 | no |
| fixed | Regenerated | 0.000 [0.000, 0.000] | 0/0/16 | no |
| fixed | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| fixed | Latency | 5,018 ms [3,376 ms, 6,590 ms] | 18/2/0 | yes |
| fixed | LLM calls | 0 [0, 0] | 0/0/20 | no |
| fixed | Tokens | 931.2 [742.2, 1,096.6] | 19/1/0 | yes |
| fixed | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
