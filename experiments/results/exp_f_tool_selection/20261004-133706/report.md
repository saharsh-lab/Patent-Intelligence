# exp_f_tool_selection — 20261004-133706

Agent with tool selection vs. every available tool on every question (Experiment F).

Dataset **real_test_v1** (53 questions, labelled by DRAFT: AI coding assistant, awaiting the team's check), 1 repeat(s), k = 5. Runs: 106 (0 failed).

> **Note:** Draft labels (DRAFT: AI coding assistant, awaiting the team's check): not verified by two people yet, so these numbers must not be reported.

## Variants

- **select** (agentic): `agent_tool_policy=select`
- **all_tools** (agentic): `agent_tool_policy=all`

## Results (mean [95% CI], n questions)

| Metric | select | all_tools |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 11.9% [8.9%, 14.9%] (n=47) | 11.9% [8.9%, 14.9%] (n=47) |
| Recall@k | 51.1% [37.2%, 63.8%] (n=47) | 51.1% [37.2%, 63.8%] (n=47) |
| MRR | 0.452 [0.326, 0.575] (n=47) | 0.449 [0.321, 0.574] (n=47) |
| Hit@k | 57.4% [42.6%, 70.2%] (n=47) | 57.4% [42.6%, 70.2%] (n=47) |
| Context precision | 10.5% [8.0%, 13.1%] (n=47) | 8.9% [6.5%, 11.4%] (n=47) |
| Context recall | 57.4% [43.6%, 70.2%] (n=47) | 55.3% [41.5%, 68.1%] (n=47) |
| Right sources found | 97.9% [93.6%, 100.0%] (n=47) | 97.9% [93.6%, 100.0%] (n=47) |
| Passages from right sources | 80.2% [71.1%, 88.0%] (n=47) | 71.5% [63.2%, 78.8%] (n=47) |
| **Answer** | | |
| Key-fact recall | 69.7% [55.3%, 84.2%] (n=38) | 67.1% [52.6%, 80.3%] (n=38) |
| Answer/abstain correct | 96.2% [90.6%, 100.0%] (n=53) | 96.2% [90.6%, 100.0%] (n=53) |
| **Grounding** | | |
| Citation coverage | 92.4% [86.6%, 97.0%] (n=47) | 91.1% [84.7%, 96.2%] (n=47) |
| Invalid citations | 0.1 [0, 0.4] (n=47) | 0.0 [0, 0.1] (n=47) |
| Grounding score | 72.5% [64.2%, 80.2%] (n=47) | 74.2% [65.5%, 81.8%] (n=47) |
| Unsupported-claim rate | 16.1% [8.4%, 25.1%] (n=47) | 14.8% [7.1%, 23.6%] (n=47) |
| Misattribution rate | 13.9% [7.7%, 21.2%] (n=47) | 13.1% [7.0%, 20.3%] (n=47) |
| Regenerated | 42.6% [29.8%, 57.4%] (n=47) | 36.2% [23.4%, 51.1%] (n=47) |
| Regeneration gain | 0.125 [0.060, 0.199] (n=20) | 0.095 [0.028, 0.175] (n=17) |
| **Comparison** | | |
| Table cells cited | 100.0% [100.0%, 100.0%] (n=7) | 100.0% [100.0%, 100.0%] (n=7) |
| Cross-source citations | 0 [0, 0] (n=7) | 0 [0, 0] (n=7) |
| **Agent** | | |
| Intent accuracy | 92.5% [84.9%, 98.1%] (n=53) | 92.5% [84.9%, 98.1%] (n=53) |
| Tool precision | 100.0% [100.0%, 100.0%] (n=53) | 77.2% [69.2%, 85.1%] (n=53) |
| Tool recall | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Tool set exact | 100.0% [100.0%, 100.0%] (n=53) | 62.3% [49.1%, 75.5%] (n=53) |
| Legal question flagged | 100.0% [100.0%, 100.0%] (n=3) | 100.0% [100.0%, 100.0%] (n=3) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 30,318 ms [25,536 ms, 35,268 ms] (n=53) | 31,578 ms [26,967 ms, 36,536 ms] (n=53) |
| LLM calls | 2.4 [2.2, 2.5] (n=53) | 2.7 [2.5, 2.8] (n=53) |
| Tokens | 3,947.2 [3,545.5, 4,381.4] (n=53) | 4,301.1 [3,876.8, 4,748.9] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- select: p50 27,996 ms, p95 61,128 ms
- all_tools: p50 27,933 ms, p95 61,453 ms

## Paired differences vs. select

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| all_tools | Precision@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| all_tools | Recall@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| all_tools | MRR | -0.003 [-0.009, 0.000] | 0/1/46 | no |
| all_tools | Hit@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| all_tools | Context precision | -0.016 [-0.030, -0.006] | 0/10/37 | yes |
| all_tools | Context recall | -0.021 [-0.064, 0.000] | 0/1/46 | no |
| all_tools | Right sources found | 0.000 [0.000, 0.000] | 0/0/47 | no |
| all_tools | Passages from right sources | -0.087 [-0.137, -0.046] | 0/11/36 | yes |
| all_tools | Key-fact recall | -0.026 [-0.079, 0.000] | 0/1/37 | no |
| all_tools | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/53 | no |
| all_tools | Citation coverage | -0.013 [-0.043, 0.005] | 1/2/44 | no |
| all_tools | Invalid citations | -0.1 [-0.3, 0] | 0/1/46 | no |
| all_tools | Grounding score | 0.017 [-0.004, 0.048] | 4/2/41 | no |
| all_tools | Unsupported-claim rate | -0.013 [-0.043, 0.011] | 2/2/43 | no |
| all_tools | Misattribution rate | -0.008 [-0.036, 0.017] | 1/3/43 | no |
| all_tools | Regenerated | -0.064 [-0.128, 0.000] | 0/3/44 | no |
| all_tools | Regeneration gain | -0.038 [-0.094, 0.000] | 0/3/14 | no |
| all_tools | Table cells cited | 0.000 [0.000, 0.000] | 0/0/7 | no |
| all_tools | Cross-source citations | 0 [0, 0] | 0/0/7 | no |
| all_tools | Intent accuracy | 0.000 [0.000, 0.000] | 0/0/53 | no |
| all_tools | Tool precision | -0.228 [-0.315, -0.149] | 0/20/33 | yes |
| all_tools | Tool recall | 0.000 [0.000, 0.000] | 0/0/53 | no |
| all_tools | Tool set exact | -0.377 [-0.509, -0.245] | 0/20/33 | yes |
| all_tools | Legal question flagged | 0.000 [0.000, 0.000] | 0/0/3 | no |
| all_tools | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| all_tools | Latency | 1,260 ms [-3,599 ms, 6,207 ms] | 27/26/0 | no |
| all_tools | LLM calls | 0.3 [0.2, 0.5] | 17/0/36 | yes |
| all_tools | Tokens | 353.9 [141.6, 595.6] | 20/3/30 | yes |
| all_tools | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
