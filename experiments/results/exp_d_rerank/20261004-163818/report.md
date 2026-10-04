# exp_d_rerank — 20261004-163818

Hybrid retrieval without vs. with cross-encoder reranking (Experiment D).

Dataset **real_test_v1** (53 questions, labelled by DRAFT: AI coding assistant, awaiting the team's check), 1 repeat(s), k = 5. Runs: 106 (0 failed).

> **Note:** Draft labels (DRAFT: AI coding assistant, awaiting the team's check): not verified by two people yet, so these numbers must not be reported.

## Variants

- **no_rerank** (baseline): `retrieval_candidate_k=30`, `reranker_enabled=False`
- **rerank** (baseline): `retrieval_candidate_k=30`, `reranker_enabled=True`, `reranker_provider=local`

## Results (mean [95% CI], n questions)

| Metric | no_rerank | rerank |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 8.9% [6.0%, 11.9%] (n=47) | 13.6% [9.8%, 17.4%] (n=47) |
| Recall@k | 39.4% [26.6%, 53.2%] (n=47) | 53.9% [40.4%, 67.0%] (n=47) |
| MRR | 0.257 [0.160, 0.358] (n=47) | 0.520 [0.382, 0.654] (n=47) |
| Hit@k | 42.6% [27.7%, 57.4%] (n=47) | 57.4% [42.6%, 70.2%] (n=47) |
| Context precision | 7.4% [5.0%, 9.9%] (n=47) | 11.3% [8.2%, 14.5%] (n=47) |
| Context recall | 39.4% [26.6%, 53.2%] (n=47) | 53.9% [40.4%, 67.0%] (n=47) |
| Right sources found | 95.7% [90.4%, 100.0%] (n=47) | 94.7% [88.3%, 98.9%] (n=47) |
| Passages from right sources | 74.5% [64.9%, 83.3%] (n=47) | 85.8% [78.0%, 92.9%] (n=47) |
| **Answer** | | |
| Key-fact recall | 60.8% [44.6%, 75.7%] (n=37) | 78.9% [65.8%, 89.5%] (n=38) |
| Answer/abstain correct | 92.5% [84.9%, 98.1%] (n=53) | 94.3% [86.8%, 100.0%] (n=53) |
| **Grounding** | | |
| Citation coverage | 81.7% [74.3%, 88.4%] (n=45) | 84.2% [77.0%, 90.8%] (n=46) |
| Invalid citations | 0.0 [0, 0.1] (n=45) | 0.0 [0, 0.1] (n=46) |
| Grounding score | 66.7% [57.0%, 75.7%] (n=45) | 68.1% [59.0%, 76.6%] (n=46) |
| Unsupported-claim rate | 22.8% [14.5%, 32.5%] (n=45) | 21.0% [13.2%, 29.8%] (n=46) |
| Misattribution rate | 11.6% [6.2%, 18.1%] (n=45) | 9.7% [5.2%, 14.9%] (n=46) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=45) | 0.0% [0.0%, 0.0%] (n=46) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 25,014 ms [22,582 ms, 27,427 ms] (n=53) | 40,423 ms [37,244 ms, 43,636 ms] (n=53) |
| LLM calls | 1 [1, 1] (n=53) | 1 [1, 1] (n=53) |
| Tokens | 2,480.3 [2,355.1, 2,602.7] (n=53) | 1,929.9 [1,778.7, 2,077.8] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- no_rerank: p50 24,444 ms, p95 38,409 ms
- rerank: p50 41,805 ms, p95 59,384 ms

## Paired differences vs. no_rerank

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| rerank | Precision@k | 0.047 [0.013, 0.081] | 13/3/31 | yes |
| rerank | Recall@k | 0.145 [0.028, 0.270] | 11/3/33 | yes |
| rerank | MRR | 0.263 [0.143, 0.388] | 20/4/23 | yes |
| rerank | Hit@k | 0.149 [0.000, 0.298] | 10/3/34 | no |
| rerank | Context precision | 0.039 [0.011, 0.067] | 13/3/31 | yes |
| rerank | Context recall | 0.145 [0.028, 0.270] | 11/3/33 | yes |
| rerank | Right sources found | -0.011 [-0.053, 0.021] | 1/2/44 | no |
| rerank | Passages from right sources | 0.113 [0.057, 0.177] | 17/2/28 | yes |
| rerank | Key-fact recall | 0.176 [0.027, 0.338] | 8/2/27 | yes |
| rerank | Answer/abstain correct | 0.019 [0.000, 0.057] | 1/0/52 | no |
| rerank | Citation coverage | 0.021 [-0.037, 0.075] | 13/9/23 | no |
| rerank | Invalid citations | 0 [-0.1, 0.1] | 1/1/43 | no |
| rerank | Grounding score | 0.007 [-0.058, 0.069] | 16/16/13 | no |
| rerank | Unsupported-claim rate | -0.013 [-0.082, 0.059] | 12/12/21 | no |
| rerank | Misattribution rate | -0.016 [-0.096, 0.064] | 9/11/25 | no |
| rerank | Regenerated | 0.000 [0.000, 0.000] | 0/0/45 | no |
| rerank | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| rerank | Latency | 15,409 ms [12,984 ms, 17,784 ms] | 49/4/0 | yes |
| rerank | LLM calls | 0 [0, 0] | 0/0/53 | no |
| rerank | Tokens | -550.3 [-665.8, -438.1] | 6/47/0 | yes |
| rerank | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
