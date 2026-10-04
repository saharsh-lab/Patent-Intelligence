# exp_a_pipelines — 20261004-013546

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
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 24.7% [20.0%, 30.6%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 86.3% [76.4%, 97.1%] (n=17) |
| MRR | 0.742 [0.592, 0.882] (n=17) | 0.749 [0.581, 0.909] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 23.5% [18.6%, 29.4%] (n=17) | 23.9% [18.8%, 29.8%] (n=17) |
| Context recall | 94.1% [85.3%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) |
| Answer/abstain correct | 95.0% [85.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 92.3% [84.5%, 98.4%] (n=16) | 94.4% [87.4%, 100.0%] (n=17) |
| Invalid citations | 0 [0, 0] (n=16) | 0 [0, 0] (n=17) |
| Grounding score | 76.7% [61.0%, 90.3%] (n=16) | 84.1% [71.2%, 94.6%] (n=17) |
| Unsupported-claim rate | 16.4% [5.1%, 30.6%] (n=16) | 9.1% [0.0%, 22.0%] (n=17) |
| Misattribution rate | 7.7% [1.6%, 15.5%] (n=16) | 7.4% [1.5%, 14.2%] (n=17) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=16) | 23.5% [5.9%, 47.1%] (n=17) |
| Regeneration gain | – | 0.198 [0.062, 0.323] (n=4) |
| **Comparison** | | |
| Table cells cited | – | 100.0% [100.0%, 100.0%] (n=2) |
| Cross-source citations | – | 0 [0, 0] (n=2) |
| **Agent** | | |
| Intent accuracy | – | 95.0% [85.0%, 100.0%] (n=20) |
| Tool precision | – | 96.2% [88.8%, 100.0%] (n=20) |
| Tool recall | – | 100.0% [100.0%, 100.0%] (n=20) |
| Tool set exact | – | 95.0% [85.0%, 100.0%] (n=20) |
| Legal question flagged | – | 100.0% (n=1) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 4,729 ms [3,395 ms, 6,151 ms] (n=20) | 10,044 ms [6,777 ms, 13,937 ms] (n=20) |
| LLM calls | 1 [1, 1] (n=20) | 2.2 [2.0, 2.4] (n=20) |
| Tokens | 861.9 [809, 911.1] (n=20) | 1,405.2 [1,219.5, 1,603.2] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- baseline: p50 3,374 ms, p95 10,680 ms
- agentic: p50 5,840 ms, p95 29,718 ms

## Paired differences vs. baseline

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| agentic | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| agentic | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| agentic | MRR | 0.007 [-0.068, 0.103] | 1/2/14 | no |
| agentic | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| agentic | Context precision | 0.004 [0.000, 0.010] | 2/0/15 | no |
| agentic | Context recall | 0.059 [0.000, 0.147] | 2/0/15 | no |
| agentic | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| agentic | Answer/abstain correct | 0.050 [0.000, 0.150] | 1/0/19 | no |
| agentic | Citation coverage | 0.018 [0.000, 0.054] | 1/0/15 | no |
| agentic | Invalid citations | 0 [0, 0] | 0/0/16 | no |
| agentic | Grounding score | 0.074 [0.016, 0.148] | 4/0/12 | yes |
| agentic | Unsupported-claim rate | -0.067 [-0.144, 0.000] | 0/3/13 | no |
| agentic | Misattribution rate | -0.004 [-0.016, 0.004] | 1/1/14 | no |
| agentic | Regenerated | 0.250 [0.062, 0.438] | 4/0/12 | yes |
| agentic | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| agentic | Latency | 5,316 ms [2,775 ms, 8,746 ms] | 20/0/0 | yes |
| agentic | LLM calls | 1.2 [1.1, 1.4] | 20/0/0 | yes |
| agentic | Tokens | 543.2 [358.6, 747.5] | 19/1/0 | yes |
| agentic | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
