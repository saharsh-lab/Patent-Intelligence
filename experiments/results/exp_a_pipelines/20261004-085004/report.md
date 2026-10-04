# exp_a_pipelines — 20261004-085004

Baseline RAG vs. agentic RAG (Experiment A).

Dataset **real_v1** (54 questions, labelled by DRAFT: AI coding assistant, not yet verified by the team), 1 repeat(s), k = 5. Runs: 108 (0 failed).

> **Note:** Draft labels (DRAFT: AI coding assistant, not yet verified by the team): not verified by two people yet, so these numbers must not be reported.

## Variants

- **baseline** (baseline): defaults
- **agentic** (agentic): defaults

## Results (mean [95% CI], n questions)

| Metric | baseline | agentic |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 9.4% [6.0%, 13.6%] (n=47) | 14.9% [11.1%, 19.1%] (n=47) |
| Recall@k | 34.0% [22.3%, 46.8%] (n=47) | 55.3% [42.6%, 68.1%] (n=47) |
| MRR | 0.271 [0.171, 0.390] (n=47) | 0.455 [0.334, 0.571] (n=47) |
| Hit@k | 38.3% [25.5%, 51.1%] (n=47) | 63.8% [51.1%, 76.6%] (n=47) |
| Context precision | 9.2% [6.0%, 12.8%] (n=47) | 12.6% [9.6%, 15.8%] (n=47) |
| Context recall | 39.4% [26.6%, 52.1%] (n=47) | 60.6% [47.9%, 72.4%] (n=47) |
| **Answer** | | |
| Key-fact recall | 75.7% [62.2%, 87.8%] (n=37) | 78.8% [65.2%, 90.9%] (n=33) |
| Answer/abstain correct | 94.4% [87.0%, 100.0%] (n=54) | 88.9% [79.6%, 96.3%] (n=54) |
| **Grounding** | | |
| Citation coverage | 79.8% [72.2%, 86.5%] (n=44) | 87.4% [81.4%, 92.9%] (n=41) |
| Invalid citations | 0.1 [0, 0.3] (n=44) | 0.1 [0, 0.2] (n=41) |
| Grounding score | 65.6% [56.9%, 73.9%] (n=44) | 77.6% [71.0%, 83.9%] (n=41) |
| Unsupported-claim rate | 20.2% [12.3%, 29.2%] (n=44) | 6.7% [2.5%, 12.0%] (n=41) |
| Misattribution rate | 15.5% [10.4%, 21.1%] (n=44) | 17.1% [10.9%, 23.8%] (n=41) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=44) | 19.5% [7.3%, 31.7%] (n=41) |
| Regeneration gain | – | 0.117 [0.042, 0.205] (n=8) |
| **Comparison** | | |
| Table cells cited | – | 100.0% [100.0%, 100.0%] (n=7) |
| Cross-source citations | – | 0 [0, 0] (n=7) |
| **Agent** | | |
| Intent accuracy | – | 83.3% [72.2%, 92.6%] (n=54) |
| Tool precision | – | 90.9% [84.4%, 97.2%] (n=54) |
| Tool recall | – | 100.0% [100.0%, 100.0%] (n=54) |
| Tool set exact | – | 87.0% [77.8%, 96.3%] (n=54) |
| Legal question flagged | – | 100.0% [100.0%, 100.0%] (n=3) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=54) | 0.0% [0.0%, 0.0%] (n=54) |
| Latency | 19,613 ms [17,040 ms, 22,493 ms] (n=54) | 23,512 ms [17,342 ms, 30,172 ms] (n=54) |
| LLM calls | 1 [1, 1] (n=54) | 2.1 [1.9, 2.2] (n=54) |
| Tokens | 2,502.5 [2,340.6, 2,652.1] (n=54) | 3,049.6 [2,621.6, 3,494.9] (n=54) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=54) | $0.0000 [$0.0000, $0.0000] (n=54) |

Latency percentiles:

- baseline: p50 19,066 ms, p95 33,168 ms
- agentic: p50 15,408 ms, p95 60,177 ms

## Paired differences vs. baseline

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| agentic | Precision@k | 0.055 [0.034, 0.081] | 13/0/34 | yes |
| agentic | Recall@k | 0.213 [0.117, 0.330] | 13/0/34 | yes |
| agentic | MRR | 0.184 [0.092, 0.296] | 13/1/33 | yes |
| agentic | Hit@k | 0.255 [0.149, 0.383] | 12/0/35 | yes |
| agentic | Context precision | 0.033 [0.016, 0.054] | 12/3/32 | yes |
| agentic | Context recall | 0.213 [0.117, 0.330] | 12/0/35 | yes |
| agentic | Key-fact recall | 0.047 [0.000, 0.125] | 2/0/30 | no |
| agentic | Answer/abstain correct | -0.056 [-0.148, 0.037] | 2/5/47 | no |
| agentic | Citation coverage | 0.101 [0.023, 0.182] | 13/2/24 | yes |
| agentic | Invalid citations | -0.1 [-0.3, 0.2] | 2/2/35 | no |
| agentic | Grounding score | 0.115 [0.035, 0.195] | 14/4/21 | yes |
| agentic | Unsupported-claim rate | -0.124 [-0.200, -0.053] | 3/13/23 | yes |
| agentic | Misattribution rate | 0.013 [-0.056, 0.091] | 5/7/27 | no |
| agentic | Regenerated | 0.205 [0.077, 0.333] | 8/0/31 | yes |
| agentic | Run failed | 0.000 [0.000, 0.000] | 0/0/54 | no |
| agentic | Latency | 3,900 ms [-1,120 ms, 9,751 ms] | 24/30/0 | no |
| agentic | LLM calls | 1.1 [0.9, 1.2] | 50/0/4 | yes |
| agentic | Tokens | 547.0 [142.0, 947.5] | 45/9/0 | yes |
| agentic | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/54 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
