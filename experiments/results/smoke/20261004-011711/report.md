# smoke — 20261004-011711

Framework check with fake models (not a research result).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 40 (0 failed).

> **Note:** Variant(s) agentic, baseline used FAKE models (canned LLM answers and/or hashing embeddings): these numbers only test the framework.
> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **baseline** (baseline): `llm_provider=fake`, `embedding_provider=fake`, `reranker_enabled=False`, `verifier_method=lexical`
- **agentic** (agentic): `llm_provider=fake`, `embedding_provider=fake`, `reranker_enabled=False`, `verifier_method=lexical`, `agent_planner=rules`

## Results (mean [95% CI], n questions)

| Metric | baseline | agentic |
|---|---|---|
| **Retrieval** | | |
| Precision@k | 23.5% [18.8%, 30.6%] (n=17) | 24.7% [20.0%, 30.6%] (n=17) |
| Recall@k | 83.3% [68.6%, 95.1%] (n=17) | 86.3% [76.4%, 97.1%] (n=17) |
| MRR | 0.637 [0.471, 0.804] (n=17) | 0.639 [0.477, 0.809] (n=17) |
| Hit@k | 94.1% [82.4%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 21.6% [17.6%, 26.5%] (n=17) | 22.0% [17.8%, 27.1%] (n=17) |
| Context recall | 89.2% [79.4%, 98.0%] (n=17) | 95.1% [87.3%, 100.0%] (n=17) |
| **Answer** | | |
| Key-fact recall | 13.3% [0.0%, 33.3%] (n=15) | 13.3% [0.0%, 33.3%] (n=15) |
| Answer/abstain correct | 85.0% [70.0%, 100.0%] (n=20) | 85.0% [70.0%, 100.0%] (n=20) |
| **Grounding** | | |
| Citation coverage | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| Invalid citations | 0 [0, 0] (n=20) | 0 [0, 0] (n=20) |
| Grounding score | 100.0% [100.0%, 100.0%] (n=18) | 100.0% [100.0%, 100.0%] (n=18) |
| Unsupported-claim rate | 0.0% [0.0%, 0.0%] (n=18) | 0.0% [0.0%, 0.0%] (n=18) |
| Misattribution rate | 0.0% [0.0%, 0.0%] (n=18) | 0.0% [0.0%, 0.0%] (n=18) |
| Regenerated | 0.0% [0.0%, 0.0%] (n=18) | 0.0% [0.0%, 0.0%] (n=18) |
| **Agent** | | |
| Intent accuracy | – | 100.0% [100.0%, 100.0%] (n=20) |
| Tool precision | – | 95.0% [85.0%, 100.0%] (n=20) |
| Tool recall | – | 95.0% [85.0%, 100.0%] (n=20) |
| Tool set exact | – | 95.0% [85.0%, 100.0%] (n=20) |
| Legal question flagged | – | 100.0% (n=1) |
| **System** | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 11 ms [10 ms, 12 ms] (n=20) | 18 ms [17 ms, 20 ms] (n=20) |
| LLM calls | 1 [1, 1] (n=20) | 0.9 [0.8, 1] (n=20) |
| Tokens | 686.4 [637.1, 733.1] (n=20) | 619.4 [509.5, 711.5] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- baseline: p50 11 ms, p95 12 ms
- agentic: p50 16 ms, p95 27 ms

## Paired differences vs. baseline

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| agentic | Precision@k | 0.012 [0.000, 0.035] | 1/0/16 | no |
| agentic | Recall@k | 0.029 [0.000, 0.088] | 1/0/16 | no |
| agentic | MRR | 0.002 [-0.136, 0.132] | 2/1/14 | no |
| agentic | Hit@k | 0.059 [0.000, 0.176] | 1/0/16 | no |
| agentic | Context precision | 0.004 [0.000, 0.010] | 2/0/15 | no |
| agentic | Context recall | 0.059 [0.000, 0.147] | 2/0/15 | no |
| agentic | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| agentic | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| agentic | Citation coverage | 0.000 [0.000, 0.000] | 0/0/20 | no |
| agentic | Invalid citations | 0 [0, 0] | 0/0/20 | no |
| agentic | Grounding score | 0.000 [0.000, 0.000] | 0/0/18 | no |
| agentic | Unsupported-claim rate | 0.000 [0.000, 0.000] | 0/0/18 | no |
| agentic | Misattribution rate | 0.000 [0.000, 0.000] | 0/0/18 | no |
| agentic | Regenerated | 0.000 [0.000, 0.000] | 0/0/18 | no |
| agentic | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| agentic | Latency | 7 ms [6 ms, 9 ms] | 20/0/0 | yes |
| agentic | LLM calls | -0.1 [-0.2, 0] | 0/2/18 | no |
| agentic | Tokens | -67 [-173.8, 0] | 0/2/18 | no |
| agentic | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
