# exp_d_rerank — 20261004-081841

Hybrid retrieval without vs. with cross-encoder reranking (Experiment D).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 40 (0 failed).

> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **no_rerank** (baseline): `retrieval_candidate_k=30`, `reranker_enabled=False`
- **rerank** (baseline): `retrieval_candidate_k=30`, `reranker_enabled=True`, `reranker_provider=local`

## Results (mean [95% CI], n questions)

| Metric | no_rerank | rerank |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 27.1% [21.2%, 34.1%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 91.2% [82.4%, 100.0%] (n=17) |
| MRR | 0.742 [0.592, 0.882] (n=17) | 0.779 [0.637, 0.917] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 23.5% [18.6%, 29.4%] (n=17) | 23.5% [18.6%, 29.4%] (n=17) |
| Context recall | 94.1% [85.3%, 100.0%] (n=17) | 94.1% [85.3%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) |
| Answer/abstain correct | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 92.3% [84.5%, 98.4%] (n=16) | 92.5% [83.1%, 100.0%] (n=16) |
| Invalid citations | 0 [0, 0] (n=16) | 0 [0, 0] (n=16) |
| Grounding score | 76.7% [61.0%, 90.3%] (n=16) | 73.4% [57.4%, 88.4%] (n=16) |
| Unsupported-claim rate | 16.4% [5.1%, 30.6%] (n=16) | 22.1% [7.9%, 36.9%] (n=16) |
| Misattribution rate | 7.7% [1.6%, 15.5%] (n=16) | 4.2% [0.0%, 11.5%] (n=16) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=16) | 0.0% [0.0%, 0.0%] (n=16) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 4,647 ms [3,327 ms, 6,058 ms] (n=20) | 10,691 ms [6,814 ms, 17,301 ms] (n=20) |
| LLM calls | 1 [1, 1] (n=20) | 1 [1, 1] (n=20) |
| Tokens | 861.9 [809, 911.1] (n=20) | 854.8 [791.5, 915.0] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- no_rerank: p50 3,430 ms, p95 9,698 ms
- rerank: p50 7,080 ms, p95 16,163 ms

## Paired differences vs. no_rerank

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| rerank | Precision@k | 0.024 [0.000, 0.059] | 2/0/15 | no |
| rerank | Recall@k | 0.049 [0.000, 0.127] | 2/0/15 | no |
| rerank | MRR | 0.037 [-0.029, 0.116] | 3/1/13 | no |
| rerank | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| rerank | Context precision | 0.000 [0.000, 0.000] | 0/0/17 | no |
| rerank | Context recall | 0.000 [0.000, 0.000] | 0/0/17 | no |
| rerank | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| rerank | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| rerank | Citation coverage | 0.002 [-0.037, 0.041] | 2/1/13 | no |
| rerank | Invalid citations | 0 [0, 0] | 0/0/16 | no |
| rerank | Grounding score | -0.033 [-0.125, 0.050] | 2/4/10 | no |
| rerank | Unsupported-claim rate | 0.057 [-0.035, 0.168] | 4/2/10 | no |
| rerank | Misattribution rate | -0.035 [-0.092, 0.003] | 1/2/13 | no |
| rerank | Regenerated | 0.000 [0.000, 0.000] | 0/0/16 | no |
| rerank | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| rerank | Latency | 6,044 ms [2,655 ms, 12,266 ms] | 20/0/0 | yes |
| rerank | LLM calls | 0 [0, 0] | 0/0/20 | no |
| rerank | Tokens | -7.1 [-46.0, 28.0] | 9/8/3 | no |
| rerank | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
