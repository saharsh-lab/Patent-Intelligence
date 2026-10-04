# exp_c_topk — 20261004-081237

top-k passages given to the LLM ∈ {3, 6, 10} (Experiment C).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 3. Runs: 60 (0 failed).

> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **k3** (baseline): `retrieval_top_k=3`
- **k6** (baseline): `retrieval_top_k=6`
- **k10** (baseline): `retrieval_top_k=10`

## Results (mean [95% CI], n questions)

| Metric | k3 | k6 | k10 |
|---|---|---|---|
| **Retrieval** | | | |
| Precision@k | 31.4% [25.5%, 37.3%] (n=17) | 31.4% [25.5%, 37.3%] (n=17) | 31.4% [25.5%, 37.3%] (n=17) |
| Recall@k | 71.6% [55.9%, 86.3%] (n=17) | 71.6% [55.9%, 86.3%] (n=17) | 71.6% [55.9%, 86.3%] (n=17) |
| MRR | 0.716 [0.539, 0.873] (n=17) | 0.742 [0.592, 0.882] (n=17) | 0.742 [0.592, 0.882] (n=17) |
| Hit@k | 88.2% [70.6%, 100.0%] (n=17) | 88.2% [70.6%, 100.0%] (n=17) | 88.2% [70.6%, 100.0%] (n=17) |
| Context precision | 31.4% [25.5%, 37.3%] (n=17) | 23.5% [18.6%, 29.4%] (n=17) | 15.1% [12.2%, 18.8%] (n=17) |
| Context recall | 71.6% [55.9%, 86.3%] (n=17) | 94.1% [85.3%, 100.0%] (n=17) | 97.1% [91.2%, 100.0%] (n=17) |
| **Answer** | | | |
| Key-fact recall | 86.7% [66.7%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) |
| Answer/abstain correct | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| **Grounding** | | | |
| Citation coverage | 83.1% [71.2%, 93.8%] (n=16) | 92.3% [84.5%, 98.4%] (n=16) | 82.2% [71.5%, 91.7%] (n=17) |
| Invalid citations | 0 [0, 0] (n=16) | 0 [0, 0] (n=16) | 0.2 [0, 0.6] (n=17) |
| Grounding score | 70.1% [56.4%, 82.5%] (n=16) | 76.7% [61.0%, 90.3%] (n=16) | 61.3% [46.0%, 75.9%] (n=17) |
| Unsupported-claim rate | 22.9% [10.4%, 36.5%] (n=16) | 16.4% [5.1%, 30.6%] (n=16) | 27.9% [14.0%, 43.6%] (n=17) |
| Misattribution rate | 10.6% [3.1%, 20.0%] (n=16) | 7.7% [1.6%, 15.5%] (n=16) | 18.3% [7.0%, 33.0%] (n=17) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=16) | 0.0% [0.0%, 0.0%] (n=16) | 0.0% [0.0%, 0.0%] (n=17) |
| **System** | | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 4,933 ms [3,874 ms, 6,184 ms] (n=20) | 5,863 ms [4,555 ms, 7,212 ms] (n=20) | 6,459 ms [5,111 ms, 7,939 ms] (n=20) |
| LLM calls | 1 [1, 1] (n=20) | 1 [1, 1] (n=20) | 1 [1, 1] (n=20) |
| Tokens | 617.8 [562.6, 671.3] (n=20) | 861.9 [809, 911.1] (n=20) | 1,169.6 [1,100.2, 1,228.5] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- k3: p50 4,276 ms, p95 10,800 ms
- k6: p50 4,702 ms, p95 11,139 ms
- k10: p50 5,791 ms, p95 11,972 ms

## Paired differences vs. k3

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| k6 | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| k6 | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| k6 | MRR | 0.026 [0.000, 0.065] | 2/0/15 | no |
| k6 | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| k6 | Context precision | -0.078 [-0.147, 0.000] | 3/12/2 | no |
| k6 | Context recall | 0.225 [0.078, 0.382] | 6/0/11 | yes |
| k6 | Key-fact recall | 0.067 [-0.133, 0.267] | 2/1/12 | no |
| k6 | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| k6 | Citation coverage | 0.092 [-0.016, 0.206] | 5/2/9 | no |
| k6 | Invalid citations | 0 [0, 0] | 0/0/16 | no |
| k6 | Grounding score | 0.066 [-0.026, 0.158] | 7/2/7 | no |
| k6 | Unsupported-claim rate | -0.065 [-0.151, 0.013] | 1/6/9 | no |
| k6 | Misattribution rate | -0.030 [-0.112, 0.042] | 1/4/11 | no |
| k6 | Regenerated | 0.000 [0.000, 0.000] | 0/0/16 | no |
| k6 | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| k6 | Latency | 930 ms [-307 ms, 2,012 ms] | 17/3/0 | no |
| k6 | LLM calls | 0 [0, 0] | 0/0/20 | no |
| k6 | Tokens | 244.1 [203.4, 283.3] | 20/0/0 | yes |
| k6 | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |
| k10 | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| k10 | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| k10 | MRR | 0.026 [0.000, 0.065] | 2/0/15 | no |
| k10 | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| k10 | Context precision | -0.163 [-0.222, -0.098] | 2/15/0 | yes |
| k10 | Context recall | 0.255 [0.098, 0.412] | 7/0/10 | yes |
| k10 | Key-fact recall | 0.067 [-0.133, 0.267] | 2/1/12 | no |
| k10 | Answer/abstain correct | 0.050 [0.000, 0.150] | 1/0/19 | no |
| k10 | Citation coverage | -0.005 [-0.153, 0.138] | 4/5/7 | no |
| k10 | Invalid citations | 0.2 [0, 0.7] | 2/0/14 | no |
| k10 | Grounding score | -0.065 [-0.198, 0.041] | 4/4/8 | no |
| k10 | Unsupported-claim rate | 0.021 [-0.094, 0.131] | 5/4/7 | no |
| k10 | Misattribution rate | 0.089 [-0.060, 0.255] | 5/3/8 | no |
| k10 | Regenerated | 0.000 [0.000, 0.000] | 0/0/16 | no |
| k10 | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| k10 | Latency | 1,526 ms [17 ms, 2,804 ms] | 16/4/0 | yes |
| k10 | LLM calls | 0 [0, 0] | 0/0/20 | no |
| k10 | Tokens | 551.8 [491.3, 615.3] | 20/0/0 | yes |
| k10 | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
