# exp_g_verification — 20261004-083144

Generation only vs. + verification vs. + verification & regeneration (Experiment G).

Dataset **dev** (20 questions, labelled by AI coding assistant (development only; not human-verified)), 1 repeat(s), k = 5. Runs: 60 (0 failed).

> **Note:** Synthetic development dataset: these numbers test the framework only and must not be reported as research results.
> **Note:** Only 20 questions: confidence intervals are wide; treat differences as indicative unless the interval excludes 0.

## Variants

- **off** (agentic): `verify_mode=off`
- **report** (agentic): `verify_mode=report`
- **regenerate** (agentic): `verify_mode=regenerate`

## Results (mean [95% CI], n questions)

| Metric | off | report | regenerate |
|---|---|---|---|
| **Retrieval** | | | |
| Precision@k | 24.7% [20.0%, 30.6%] (n=17) | 24.7% [20.0%, 30.6%] (n=17) | 24.7% [20.0%, 30.6%] (n=17) |
| Recall@k | 86.3% [76.4%, 97.1%] (n=17) | 86.3% [76.4%, 97.1%] (n=17) | 86.3% [76.4%, 97.1%] (n=17) |
| MRR | 0.749 [0.581, 0.909] (n=17) | 0.749 [0.581, 0.909] (n=17) | 0.749 [0.581, 0.909] (n=17) |
| Hit@k | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| Context precision | 23.9% [18.8%, 29.8%] (n=17) | 23.9% [18.8%, 29.8%] (n=17) | 23.9% [18.8%, 29.8%] (n=17) |
| Context recall | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| **Answer** | | | |
| Key-fact recall | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) | 93.3% [80.0%, 100.0%] (n=15) |
| Answer/abstain correct | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| **Grounding** | | | |
| Citation coverage | 94.4% [87.4%, 100.0%] (n=17) | 94.4% [87.4%, 100.0%] (n=17) | 94.4% [87.4%, 100.0%] (n=17) |
| Invalid citations | 0 [0, 0] (n=17) | 0 [0, 0] (n=17) | 0 [0, 0] (n=17) |
| Grounding score | – | 79.4% [65.8%, 91.6%] (n=17) | 84.1% [71.2%, 94.6%] (n=17) |
| Unsupported-claim rate | – | 12.5% [2.5%, 24.9%] (n=17) | 9.1% [0.0%, 22.0%] (n=17) |
| Misattribution rate | – | 7.8% [2.0%, 15.2%] (n=17) | 7.4% [1.5%, 14.2%] (n=17) |
| Regenerated | – | 0.0% [0.0%, 0.0%] (n=17) | 23.5% [5.9%, 47.1%] (n=17) |
| Regeneration gain | – | – | 0.198 [0.062, 0.323] (n=4) |
| **Comparison** | | | |
| Table cells cited | 100.0% [100.0%, 100.0%] (n=2) | 100.0% [100.0%, 100.0%] (n=2) | 100.0% [100.0%, 100.0%] (n=2) |
| Cross-source citations | 0 [0, 0] (n=2) | 0 [0, 0] (n=2) | 0 [0, 0] (n=2) |
| **Agent** | | | |
| Intent accuracy | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| Tool precision | 96.2% [88.8%, 100.0%] (n=20) | 96.2% [88.8%, 100.0%] (n=20) | 96.2% [88.8%, 100.0%] (n=20) |
| Tool recall | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) | 100.0% [100.0%, 100.0%] (n=20) |
| Tool set exact | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) | 95.0% [85.0%, 100.0%] (n=20) |
| Legal question flagged | 100.0% (n=1) | 100.0% (n=1) | 100.0% (n=1) |
| **System** | | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) | 0.0% [0.0%, 0.0%] (n=20) |
| Latency | 11,138 ms [7,262 ms, 15,590 ms] (n=20) | 8,392 ms [5,544 ms, 12,035 ms] (n=20) | 9,722 ms [6,412 ms, 13,657 ms] (n=20) |
| LLM calls | 2 [2, 2] (n=20) | 2 [2, 2] (n=20) | 2.2 [2.0, 2.4] (n=20) |
| Tokens | 1,232.6 [1,094.6, 1,401.3] (n=20) | 1,232.6 [1,094.6, 1,401.3] (n=20) | 1,405.2 [1,219.5, 1,603.2] (n=20) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) | $0.0000 [$0.0000, $0.0000] (n=20) |

Latency percentiles:

- off: p50 7,701 ms, p95 30,315 ms
- report: p50 6,758 ms, p95 28,297 ms
- regenerate: p50 5,324 ms, p95 28,816 ms

## Paired differences vs. off

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| report | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | MRR | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | Context precision | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | Context recall | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| report | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| report | Citation coverage | 0.000 [0.000, 0.000] | 0/0/17 | no |
| report | Invalid citations | 0 [0, 0] | 0/0/17 | no |
| report | Table cells cited | 0.000 [0.000, 0.000] | 0/0/2 | no |
| report | Cross-source citations | 0 [0, 0] | 0/0/2 | no |
| report | Intent accuracy | 0.000 [0.000, 0.000] | 0/0/20 | no |
| report | Tool precision | 0.000 [0.000, 0.000] | 0/0/20 | no |
| report | Tool recall | 0.000 [0.000, 0.000] | 0/0/20 | no |
| report | Tool set exact | 0.000 [0.000, 0.000] | 0/0/20 | no |
| report | Legal question flagged | 0.000 | 0/0/1 | no |
| report | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| report | Latency | -2,746 ms [-7,317 ms, 774 ms] | 12/8/0 | no |
| report | LLM calls | 0 [0, 0] | 0/0/20 | no |
| report | Tokens | 0 [0, 0] | 0/0/20 | no |
| report | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |
| regenerate | Precision@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | Recall@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | MRR | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | Hit@k | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | Context precision | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | Context recall | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/15 | no |
| regenerate | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/20 | no |
| regenerate | Citation coverage | 0.000 [0.000, 0.000] | 0/0/17 | no |
| regenerate | Invalid citations | 0 [0, 0] | 0/0/17 | no |
| regenerate | Table cells cited | 0.000 [0.000, 0.000] | 0/0/2 | no |
| regenerate | Cross-source citations | 0 [0, 0] | 0/0/2 | no |
| regenerate | Intent accuracy | 0.000 [0.000, 0.000] | 0/0/20 | no |
| regenerate | Tool precision | 0.000 [0.000, 0.000] | 0/0/20 | no |
| regenerate | Tool recall | 0.000 [0.000, 0.000] | 0/0/20 | no |
| regenerate | Tool set exact | 0.000 [0.000, 0.000] | 0/0/20 | no |
| regenerate | Legal question flagged | 0.000 | 0/0/1 | no |
| regenerate | Run failed | 0.000 [0.000, 0.000] | 0/0/20 | no |
| regenerate | Latency | -1,416 ms [-6,090 ms, 2,448 ms] | 11/9/0 | no |
| regenerate | LLM calls | 0.2 [0.1, 0.4] | 4/0/16 | yes |
| regenerate | Tokens | 172.6 [40.6, 335.0] | 4/0/16 | yes |
| regenerate | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/20 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
