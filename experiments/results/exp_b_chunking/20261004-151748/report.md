# exp_b_chunking — 20261004-151748

Section-aware vs. fixed-size chunking (Experiment B).

Dataset **real_test_v1** (53 questions, labelled by DRAFT: AI coding assistant, awaiting the team's check), 1 repeat(s), k = 5. Runs: 106 (0 failed).

> **Note:** Draft labels (DRAFT: AI coding assistant, awaiting the team's check): not verified by two people yet, so these numbers must not be reported.

## Variants

- **section_aware** (baseline): `chunking_strategy=section_aware`
- **fixed** (baseline): `chunking_strategy=fixed`

## Results (mean [95% CI], n questions)

| Metric | section_aware | fixed |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 9.4% [6.4%, 12.3%] (n=47) | 12.8% [8.9%, 16.6%] (n=47) |
| Recall@k | 41.5% [28.7%, 55.3%] (n=47) | 49.6% [35.8%, 63.5%] (n=47) |
| MRR | 0.261 [0.166, 0.360] (n=47) | 0.351 [0.246, 0.467] (n=47) |
| Hit@k | 44.7% [29.8%, 59.6%] (n=47) | 55.3% [40.4%, 68.1%] (n=47) |
| Context precision | 7.8% [5.3%, 10.3%] (n=47) | 11.3% [8.2%, 14.5%] (n=47) |
| Context recall | 41.5% [28.7%, 55.3%] (n=47) | 51.8% [37.9%, 65.6%] (n=47) |
| Right sources found | 95.7% [90.4%, 100.0%] (n=47) | 93.6% [86.2%, 98.9%] (n=47) |
| Passages from right sources | 74.8% [65.2%, 83.7%] (n=47) | 78.7% [69.5%, 87.2%] (n=47) |
| **Answer** | | |
| Key-fact recall | 70.8% [55.6%, 84.7%] (n=36) | 71.1% [55.3%, 84.2%] (n=38) |
| Answer/abstain correct | 90.6% [83.0%, 98.1%] (n=53) | 96.2% [90.6%, 100.0%] (n=53) |
| **Grounding** | | |
| Citation coverage | 80.4% [73.5%, 86.8%] (n=44) | 75.8% [66.7%, 84.4%] (n=45) |
| Invalid citations | 0.0 [0, 0.1] (n=44) | 0.2 [0.0, 0.4] (n=45) |
| Grounding score | 65.3% [55.8%, 74.3%] (n=44) | 48.0% [38.5%, 57.7%] (n=45) |
| Unsupported-claim rate | 24.8% [16.2%, 34.8%] (n=44) | 36.8% [25.8%, 48.4%] (n=45) |
| Misattribution rate | 11.8% [6.5%, 17.8%] (n=44) | 15.1% [8.9%, 22.3%] (n=45) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=44) | 0.0% [0.0%, 0.0%] (n=45) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 18,443 ms [16,681 ms, 20,099 ms] (n=53) | 23,771 ms [21,423 ms, 26,612 ms] (n=53) |
| LLM calls | 1 [1, 1] (n=53) | 1 [1, 1] (n=53) |
| Tokens | 2,468.3 [2,342.2, 2,589.9] (n=53) | 3,219.5 [3,171.8, 3,277.4] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- section_aware: p50 19,821 ms, p95 27,038 ms
- fixed: p50 23,779 ms, p95 32,133 ms

## Paired differences vs. section_aware

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| fixed | Precision@k | 0.034 [0.004, 0.064] | 11/3/33 | yes |
| fixed | Recall@k | 0.082 [-0.035, 0.209] | 9/3/35 | no |
| fixed | MRR | 0.090 [-0.015, 0.197] | 15/7/25 | no |
| fixed | Hit@k | 0.106 [-0.021, 0.255] | 8/3/36 | no |
| fixed | Context precision | 0.035 [0.011, 0.060] | 13/3/31 | yes |
| fixed | Context recall | 0.103 [-0.021, 0.230] | 10/3/34 | no |
| fixed | Right sources found | -0.021 [-0.064, 0.000] | 0/1/46 | no |
| fixed | Passages from right sources | 0.039 [0.004, 0.071] | 13/4/30 | yes |
| fixed | Key-fact recall | -0.043 [-0.229, 0.143] | 5/6/24 | no |
| fixed | Answer/abstain correct | 0.057 [-0.019, 0.151] | 4/1/48 | no |
| fixed | Citation coverage | -0.056 [-0.134, 0.012] | 7/15/20 | no |
| fixed | Invalid citations | 0.2 [0.0, 0.4] | 4/0/38 | yes |
| fixed | Grounding score | -0.185 [-0.298, -0.067] | 10/25/7 | yes |
| fixed | Unsupported-claim rate | 0.124 [-0.007, 0.258] | 18/10/14 | no |
| fixed | Misattribution rate | 0.035 [-0.051, 0.114] | 15/9/18 | no |
| fixed | Regenerated | 0.000 [0.000, 0.000] | 0/0/42 | no |
| fixed | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| fixed | Latency | 5,329 ms [3,133 ms, 8,019 ms] | 49/4/0 | yes |
| fixed | LLM calls | 0 [0, 0] | 0/0/53 | no |
| fixed | Tokens | 751.2 [637.2, 872.3] | 53/0/0 | yes |
| fixed | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
