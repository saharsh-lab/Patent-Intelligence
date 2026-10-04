# exp_e_live — 20261004-150821

Brand-new EPO patents answered with live data, local data only, or the LLM alone (Experiment E).

30 questions about 15 patents published 2026-04-15 to 2026-09-30, fetched live (automatic: claim text fetched live from the patent office). Runs: 30 (0 failed).

> **Note:** Ground truth is the patent's own claim text and abstract, fetched live and frozen in the question set; 'supported by the patent' is the NLI verifier's judgement against them (strict; see Experiment I). Statements drawn from the description are not covered by these premises and count as unsupported.

| Metric | local_only |
|---|---|
| Said it could not answer | 100.0% [100.0%, 100.0%] |
| Evidence from the asked patent | 0.0% [0.0%, 0.0%] |
| Asked claim retrieved | 0.0% [0.0%, 0.0%] |
| Claim content in the answer | 0.0% [0.0%, 0.0%] |
| Statements supported by the patent | – |
| Statements contradicted/unsupported | – |
| Latency | 2,459 [2,380, 2,528] |
| Tokens | 327 [325, 329] |

*Mean [95% bootstrap CI] over questions.*

## Paired differences vs. live

| Variant | Metric | Δ mean [95% CI] | clear? |
|---|---|---|---|
