# exp_f_tool_selection — 20261004-082407

Agent with tool selection vs. every available tool on every question (Experiment F).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 40 (0 failed).

> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **select** (agentic): `agent_tool_policy=select`
- **all_tools** (agentic): `agent_tool_policy=all`

## Results (mean [95% CI], n questions)

| Metric | select | all_tools |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 24.7% [20.0%, 30.6%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 86.3% [76.4%, 97.1%] (n=17) |
| MRR | 0.749 [0.581, 0.909] (n=17) | 0.749 [0.581, 0.909] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 23.9% [18.8%, 29.8%] (n=17) | 22.5% [16.9%, 29.0%] (n=17) |
| Context recall | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) |
| Answer/abstain correct | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 94.4% [87.4%, 100.0%] (n=17) | 95.6% [88.2%, 100.0%] (n=17) |
| Invalid citations | 0 [0, 0] (n=17) | 0 [0, 0] (n=17) |
| Grounding score | 84.1% [71.2%, 94.6%] (n=17) | 85.0% [74.8%, 93.6%] (n=17) |
| Unsupported-claim rate | 9.1% [0.0%, 22.0%] (n=17) | 7.8% [0.0%, 18.6%] (n=17) |
| Misattribution rate | 7.4% [1.5%, 14.2%] (n=17) | 9.3% [2.9%, 16.7%] (n=17) |
| Regenerated | 23.5% [5.9%, 47.1%] (n=17) | 23.5% [5.9%, 47.1%] (n=17) |
| Regeneration gain | 0.198 [0.062, 0.323] (n=4) | 0.198 [0.062, 0.323] (n=4) |
| **Comparison** | | |
| Table cells cited | 100.0% [100.0%, 100.0%] (n=2) | 100.0% [100.0%, 100.0%] (n=2) |
| Cross-source citations | 0 [0, 0] (n=2) | 0 [0, 0] (n=2) |
| **Agent** | | |
| Intent accuracy | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| Tool precision | 96.2% [88.8%, 100.0%] (n=20) | 76.4% [62.8%, 88.8%] (n=20) |
| Tool recall | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| Tool set exact | 95.0% [85.0%, 100.0%] (n=20) | 60.0% [40.0%, 80.0%] (n=20) |
| Legal question flagged | 100.0% (n=1) | 100.0% (n=1) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 11,412 ms [7,906 ms, 15,580 ms] (n=20) | 10,544 ms [7,335 ms, 14,597 ms] (n=20) |
| LLM calls | 2.2 [2.0, 2.4] (n=20) | 2.5 [2.3, 2.9] (n=20) |
| Tokens | 1,405.2 [1,219.5, 1,603.2] (n=20) | 1,550.3 [1,321.9, 1,798.8] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- select: p50 7,434 ms, p95 32,302 ms
- all_tools: p50 7,311 ms, p95 29,223 ms

## Paired differences vs. select

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| all_tools | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| all_tools | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| all_tools | MRR | 0.000 [0.000, 0.000] | 0/0/17 | no |
| all_tools | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| all_tools | Context precision | -0.014 [-0.028, -0.003] | 0/4/13 | yes |
| all_tools | Context recall | 0.000 [0.000, 0.000] | 0/0/17 | no |
| all_tools | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| all_tools | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| all_tools | Citation coverage | 0.012 [0.000, 0.035] | 1/0/16 | no |
| all_tools | Invalid citations | 0 [0, 0] | 0/0/17 | no |
| all_tools | Grounding score | 0.009 [-0.020, 0.038] | 2/1/14 | no |
| all_tools | Unsupported-claim rate | -0.013 [-0.035, 0.000] | 0/2/15 | no |
| all_tools | Misattribution rate | 0.020 [0.000, 0.059] | 1/0/16 | no |
| all_tools | Regenerated | 0.000 [0.000, 0.000] | 0/0/17 | no |
| all_tools | Regeneration gain | 0.000 [0.000, 0.000] | 1/0/3 | no |
| all_tools | Table cells cited | 0.000 [0.000, 0.000] | 0/0/2 | no |
| all_tools | Cross-source citations | 0 [0, 0] | 0/0/2 | no |
| all_tools | Intent accuracy | 0.000 [0.000, 0.000] | 0/0/20 | no |
| all_tools | Tool precision | -0.198 [-0.328, -0.086] | 1/7/12 | yes |
| all_tools | Tool recall | 0.000 [0.000, 0.000] | 0/0/20 | no |
| all_tools | Tool set exact | -0.350 [-0.550, -0.150] | 0/7/13 | yes |
| all_tools | Legal question flagged | 0.000 | 0/0/1 | no |
| all_tools | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| all_tools | Latency | -868 ms [-1,813 ms, 330 ms] | 4/16/0 | no |
| all_tools | LLM calls | 0.3 [0.1, 0.6] | 7/0/13 | yes |
| all_tools | Tokens | 145.2 [60.2, 236.5] | 7/0/13 | yes |
| all_tools | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
