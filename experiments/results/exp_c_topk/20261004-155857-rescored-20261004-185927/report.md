# exp_c_topk — 20261004-155857-rescored-20261004-185927

top-k passages given to the LLM ∈ {3, 6, 10} (Experiment C).

Dataset **real_test_v1** (53 questions, labelled by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified), 1 repeat(s), k = 3. Runs: 159 (0 failed).

> **Note:** Rescored from run 20261004-155857 with the current labels and scoring code (the answers themselves were not regenerated).
> **Note:** Limitation: labels by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified. State this wherever these numbers are reported.

## Variants

- **k3** (baseline): `retrieval_top_k=3`
- **k6** (baseline): `retrieval_top_k=6`
- **k10** (baseline): `retrieval_top_k=10`

## Results (mean [95% CI], n questions)

| Metric | k3 | k6 | k10 |
|---|---|---|---|
| **Retrieval** | | | |
| Precision@k | 13.5% [9.2%, 18.4%] (n=47) | 13.5% [9.2%, 18.4%] (n=47) | 13.5% [9.2%, 18.4%] (n=47) |
| Recall@k | 37.2% [24.5%, 50.0%] (n=47) | 37.2% [24.5%, 50.0%] (n=47) | 37.2% [24.5%, 50.0%] (n=47) |
| MRR | 0.259 [0.160, 0.362] (n=47) | 0.268 [0.170, 0.371] (n=47) | 0.278 [0.180, 0.379] (n=47) |
| Hit@k | 40.4% [27.7%, 55.3%] (n=47) | 40.4% [27.7%, 55.3%] (n=47) | 40.4% [27.7%, 55.3%] (n=47) |
| Context precision | 13.5% [9.2%, 18.4%] (n=47) | 7.8% [5.3%, 10.3%] (n=47) | 6.0% [4.3%, 7.7%] (n=47) |
| Context recall | 37.2% [24.5%, 50.0%] (n=47) | 41.5% [28.7%, 55.3%] (n=47) | 50.0% [36.2%, 62.8%] (n=47) |
| Right sources found | 91.5% [84.0%, 96.8%] (n=47) | 95.7% [90.4%, 100.0%] (n=47) | 95.7% [90.4%, 100.0%] (n=47) |
| Passages from right sources | 80.9% [71.6%, 89.4%] (n=47) | 74.8% [65.2%, 83.7%] (n=47) | 68.7% [58.5%, 78.3%] (n=47) |
| **Answer** | | | |
| Key-fact recall | 59.2% [43.4%, 73.7%] (n=38) | 71.6% [55.4%, 85.1%] (n=37) | 74.3% [59.5%, 87.8%] (n=37) |
| Answer/abstain correct | 94.3% [86.8%, 100.0%] (n=53) | 92.5% [84.9%, 98.1%] (n=53) | 92.5% [84.9%, 98.1%] (n=53) |
| **Grounding** | | | |
| Citation coverage | 72.0% [63.3%, 80.5%] (n=44) | 77.9% [69.0%, 85.4%] (n=45) | 77.5% [68.0%, 86.3%] (n=45) |
| Invalid citations | 0.1 [0, 0.1] (n=44) | 0.0 [0, 0.1] (n=45) | 0.0 [0, 0.1] (n=45) |
| Grounding score | 57.7% [48.5%, 67.3%] (n=44) | 64.0% [54.4%, 73.2%] (n=45) | 64.2% [54.4%, 73.5%] (n=45) |
| Unsupported-claim rate | 29.3% [19.4%, 39.0%] (n=44) | 25.5% [16.9%, 35.6%] (n=45) | 23.3% [15.2%, 32.8%] (n=45) |
| Misattribution rate | 16.0% [8.9%, 24.0%] (n=44) | 11.8% [6.6%, 18.2%] (n=45) | 15.5% [9.0%, 23.1%] (n=45) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=44) | 0.0% [0.0%, 0.0%] (n=45) | 0.0% [0.0%, 0.0%] (n=45) |
| **System** | | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 10,496 ms [9,258 ms, 11,846 ms] (n=53) | 14,669 ms [12,874 ms, 16,493 ms] (n=53) | 16,431 ms [14,193 ms, 18,766 ms] (n=53) |
| LLM calls | 1 [1, 1] (n=53) | 1 [1, 1] (n=53) | 1 [1, 1] (n=53) |
| Tokens | 1,446.9 [1,376.5, 1,509.6] (n=53) | 2,461.7 [2,331.9, 2,588.1] (n=53) | 3,395.2 [3,263.1, 3,513.3] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- k3: p50 10,708 ms, p95 18,545 ms
- k6: p50 15,212 ms, p95 25,174 ms
- k10: p50 15,213 ms, p95 30,475 ms

## Paired differences vs. k3

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| k6 | Precision@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| k6 | Recall@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| k6 | MRR | 0.010 [0.000, 0.024] | 2/0/45 | no |
| k6 | Hit@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| k6 | Context precision | -0.057 [-0.085, -0.032] | 2/18/27 | yes |
| k6 | Context recall | 0.043 [0.000, 0.106] | 2/0/45 | no |
| k6 | Right sources found | 0.043 [0.000, 0.106] | 3/0/44 | no |
| k6 | Passages from right sources | -0.060 [-0.103, -0.014] | 3/15/29 | yes |
| k6 | Key-fact recall | 0.108 [0.027, 0.216] | 5/0/32 | yes |
| k6 | Answer/abstain correct | -0.019 [-0.094, 0.038] | 1/2/50 | no |
| k6 | Citation coverage | 0.077 [0.006, 0.151] | 14/8/21 | yes |
| k6 | Invalid citations | -0.0 [-0.1, 0.0] | 1/3/39 | no |
| k6 | Grounding score | 0.062 [0.003, 0.123] | 20/11/12 | yes |
| k6 | Unsupported-claim rate | -0.035 [-0.107, 0.040] | 10/12/21 | no |
| k6 | Misattribution rate | -0.048 [-0.119, 0.020] | 10/10/23 | no |
| k6 | Regenerated | 0.000 [0.000, 0.000] | 0/0/43 | no |
| k6 | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| k6 | Latency | 4,173 ms [2,481 ms, 5,991 ms] | 36/17/0 | yes |
| k6 | LLM calls | 0 [0, 0] | 0/0/53 | no |
| k6 | Tokens | 1,014.8 [933.5, 1,092.4] | 53/0/0 | yes |
| k6 | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |
| k10 | Precision@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| k10 | Recall@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| k10 | MRR | 0.019 [0.006, 0.036] | 6/0/41 | yes |
| k10 | Hit@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| k10 | Context precision | -0.075 [-0.111, -0.042] | 6/19/22 | yes |
| k10 | Context recall | 0.128 [0.043, 0.223] | 7/0/40 | yes |
| k10 | Right sources found | 0.043 [0.000, 0.106] | 3/0/44 | no |
| k10 | Passages from right sources | -0.121 [-0.181, -0.062] | 4/21/22 | yes |
| k10 | Key-fact recall | 0.135 [0.013, 0.270] | 7/1/29 | yes |
| k10 | Answer/abstain correct | -0.019 [-0.094, 0.038] | 1/2/50 | no |
| k10 | Citation coverage | 0.057 [-0.034, 0.156] | 16/10/17 | no |
| k10 | Invalid citations | -0.0 [-0.1, 0.0] | 1/3/39 | no |
| k10 | Grounding score | 0.057 [-0.009, 0.138] | 20/11/12 | no |
| k10 | Unsupported-claim rate | -0.049 [-0.134, 0.025] | 10/14/19 | no |
| k10 | Misattribution rate | -0.007 [-0.084, 0.072] | 10/11/22 | no |
| k10 | Regenerated | 0.000 [0.000, 0.000] | 0/0/43 | no |
| k10 | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| k10 | Latency | 5,935 ms [3,806 ms, 8,132 ms] | 38/15/0 | yes |
| k10 | LLM calls | 0 [0, 0] | 0/0/53 | no |
| k10 | Tokens | 1,948.2 [1,860.9, 2,026.1] | 53/0/0 | yes |
| k10 | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
