# exp_g_verification — 20261004-123801-rescored-20261004-185931

Generation only vs. + verification vs. + verification & regeneration (Experiment G).

Dataset **real_test_v1** (53 questions, labelled by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified), 1 repeat(s), k = 5. Runs: 159 (0 failed).

> **Note:** Rescored from run 20261004-123801 with the current labels and scoring code (the answers themselves were not regenerated).
> **Note:** Limitation: labels by AI coding assistant (drafted, then audited item by item on 2026-10-04); not human-verified. State this wherever these numbers are reported.

## Variants

- **off** (agentic): `verify_mode=off`
- **report** (agentic): `verify_mode=report`
- **regenerate** (agentic): `verify_mode=regenerate`

## Results (mean [95% CI], n questions)

| Metric | off | report | regenerate |
|---|---|---|---|
| **Retrieval** | | | |
| Precision@k | 12.3% [9.4%, 15.3%] (n=47) | 12.3% [9.4%, 15.3%] (n=47) | 12.3% [9.4%, 15.3%] (n=47) |
| Recall@k | 53.2% [40.4%, 66.0%] (n=47) | 53.2% [40.4%, 66.0%] (n=47) | 53.2% [40.4%, 66.0%] (n=47) |
| MRR | 0.454 [0.330, 0.578] (n=47) | 0.454 [0.330, 0.578] (n=47) | 0.460 [0.338, 0.583] (n=47) |
| Hit@k | 59.6% [44.7%, 72.3%] (n=47) | 59.6% [44.7%, 72.3%] (n=47) | 59.6% [44.7%, 72.3%] (n=47) |
| Context precision | 10.5% [8.0%, 12.9%] (n=47) | 10.5% [8.0%, 12.9%] (n=47) | 11.2% [8.7%, 13.8%] (n=47) |
| Context recall | 57.4% [43.6%, 70.2%] (n=47) | 57.4% [43.6%, 70.2%] (n=47) | 60.6% [47.8%, 73.4%] (n=47) |
| Right sources found | 97.9% [93.6%, 100.0%] (n=47) | 97.9% [93.6%, 100.0%] (n=47) | 97.9% [93.6%, 100.0%] (n=47) |
| Passages from right sources | 80.9% [72.0%, 88.3%] (n=47) | 80.9% [72.0%, 88.3%] (n=47) | 80.8% [72.0%, 88.3%] (n=47) |
| **Answer** | | | |
| Key-fact recall | 75.0% [61.8%, 86.8%] (n=38) | 75.0% [61.8%, 86.8%] (n=38) | 75.0% [61.8%, 86.8%] (n=38) |
| Answer/abstain correct | 96.2% [90.6%, 100.0%] (n=53) | 96.2% [90.6%, 100.0%] (n=53) | 96.2% [90.6%, 100.0%] (n=53) |
| **Grounding** | | | |
| Citation coverage | 85.6% [79.6%, 91.3%] (n=47) | 85.6% [79.6%, 91.3%] (n=47) | 91.9% [86.3%, 96.3%] (n=47) |
| Invalid citations | 0.1 [0, 0.4] (n=47) | 0.1 [0, 0.4] (n=47) | 0.1 [0, 0.4] (n=47) |
| Grounding score | – | 68.7% [59.5%, 77.0%] (n=47) | 72.7% [64.2%, 80.4%] (n=47) |
| Unsupported-claim rate | – | 21.3% [13.7%, 30.2%] (n=47) | 18.2% [11.0%, 27.0%] (n=47) |
| Misattribution rate | – | 11.4% [6.1%, 17.9%] (n=47) | 12.1% [6.3%, 18.8%] (n=47) |
| Regenerated | – | 0.0% [0.0%, 0.0%] (n=47) | 42.6% [29.8%, 57.4%] (n=47) |
| Regeneration gain | – | – | 0.089 [0.036, 0.150] (n=20) |
| **Comparison** | | | |
| Table cells cited | 100.0% [100.0%, 100.0%] (n=7) | 100.0% [100.0%, 100.0%] (n=7) | 100.0% [100.0%, 100.0%] (n=7) |
| Cross-source citations | 0 [0, 0] (n=7) | 0 [0, 0] (n=7) | 0 [0, 0] (n=7) |
| **Agent** | | | |
| Intent accuracy | 92.5% [84.9%, 98.1%] (n=53) | 92.5% [84.9%, 98.1%] (n=53) | 92.5% [84.9%, 98.1%] (n=53) |
| Tool precision | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Tool recall | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Tool set exact | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) | 100.0% [100.0%, 100.0%] (n=53) |
| Legal question flagged | 100.0% [100.0%, 100.0%] (n=3) | 100.0% [100.0%, 100.0%] (n=3) | 100.0% [100.0%, 100.0%] (n=3) |
| **System** | | | |
| Run failed | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) | 0.0% [0.0%, 0.0%] (n=53) |
| Latency | 13,188 ms [11,314 ms, 15,263 ms] (n=53) | 20,711 ms [15,962 ms, 26,933 ms] (n=53) | 29,648 ms [22,648 ms, 38,969 ms] (n=53) |
| LLM calls | 2 [2, 2] (n=53) | 2 [2, 2] (n=53) | 2.4 [2.2, 2.5] (n=53) |
| Tokens | 2,834.9 [2,697.6, 2,965.8] (n=53) | 2,834.9 [2,697.6, 2,965.8] (n=53) | 3,975.7 [3,549.2, 4,420.2] (n=53) |
| Cost | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) | $0.0000 [$0.0000, $0.0000] (n=53) |

Latency percentiles:

- off: p50 11,375 ms, p95 29,225 ms
- report: p50 16,001 ms, p95 39,024 ms
- regenerate: p50 26,394 ms, p95 53,931 ms

## Paired differences vs. off

| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |
|---|---|---|---|---|
| report | Precision@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Recall@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | MRR | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Hit@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Context precision | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Context recall | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Right sources found | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Passages from right sources | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Key-fact recall | 0.000 [0.000, 0.000] | 0/0/38 | no |
| report | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/53 | no |
| report | Citation coverage | 0.000 [0.000, 0.000] | 0/0/47 | no |
| report | Invalid citations | 0 [0, 0] | 0/0/47 | no |
| report | Table cells cited | 0.000 [0.000, 0.000] | 0/0/7 | no |
| report | Cross-source citations | 0 [0, 0] | 0/0/7 | no |
| report | Intent accuracy | 0.000 [0.000, 0.000] | 0/0/53 | no |
| report | Tool precision | 0.000 [0.000, 0.000] | 0/0/53 | no |
| report | Tool recall | 0.000 [0.000, 0.000] | 0/0/53 | no |
| report | Tool set exact | 0.000 [0.000, 0.000] | 0/0/53 | no |
| report | Legal question flagged | 0.000 [0.000, 0.000] | 0/0/3 | no |
| report | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| report | Latency | 7,523 ms [3,634 ms, 12,341 ms] | 40/13/0 | yes |
| report | LLM calls | 0 [0, 0] | 0/0/53 | no |
| report | Tokens | 0 [0, 0] | 0/0/53 | no |
| report | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |
| regenerate | Precision@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| regenerate | Recall@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| regenerate | MRR | 0.006 [0.000, 0.015] | 2/0/45 | no |
| regenerate | Hit@k | 0.000 [0.000, 0.000] | 0/0/47 | no |
| regenerate | Context precision | 0.008 [-0.001, 0.022] | 2/1/44 | no |
| regenerate | Context recall | 0.032 [0.000, 0.085] | 2/0/45 | no |
| regenerate | Right sources found | 0.000 [0.000, 0.000] | 0/0/47 | no |
| regenerate | Passages from right sources | -0.000 [-0.010, 0.007] | 3/1/43 | no |
| regenerate | Key-fact recall | 0.000 [-0.079, 0.079] | 1/1/36 | no |
| regenerate | Answer/abstain correct | 0.000 [0.000, 0.000] | 0/0/53 | no |
| regenerate | Citation coverage | 0.063 [0.023, 0.111] | 8/1/38 | yes |
| regenerate | Invalid citations | 0 [0, 0] | 0/0/47 | no |
| regenerate | Table cells cited | 0.000 [0.000, 0.000] | 0/0/7 | no |
| regenerate | Cross-source citations | 0 [0, 0] | 0/0/7 | no |
| regenerate | Intent accuracy | 0.000 [0.000, 0.000] | 0/0/53 | no |
| regenerate | Tool precision | 0.000 [0.000, 0.000] | 0/0/53 | no |
| regenerate | Tool recall | 0.000 [0.000, 0.000] | 0/0/53 | no |
| regenerate | Tool set exact | 0.000 [0.000, 0.000] | 0/0/53 | no |
| regenerate | Legal question flagged | 0.000 [0.000, 0.000] | 0/0/3 | no |
| regenerate | Run failed | 0.000 [0.000, 0.000] | 0/0/53 | no |
| regenerate | Latency | 16,460 ms [10,410 ms, 24,563 ms] | 44/9/0 | yes |
| regenerate | LLM calls | 0.4 [0.3, 0.5] | 20/0/33 | yes |
| regenerate | Tokens | 1,140.8 [763.8, 1,543.3] | 20/0/33 | yes |
| regenerate | Cost | $0.0000 [$0.0000, $0.0000] | 0/0/53 | no |

'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this dataset (not the same as 'no difference').
