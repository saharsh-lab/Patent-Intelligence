# exp_e_live — 20261004-143512

Brand-new EPO patents answered with live data, local data only, or the LLM alone (Experiment E).

30 questions about 15 patents published 2026-04-15 to 2026-09-30, fetched live (automatic: claim text fetched live from the patent office). Runs: 90 (0 failed).

> **Note:** Ground truth is the patent's own claim text and abstract, fetched live and frozen in the question set; 'supported by the patent' is the NLI verifier's judgement against them (strict; see Experiment I). Statements drawn from the description are not covered by these premises and count as unsupported.

| Metric | live | local_only | closed_book |
|---|---|---|---|
| Said it could not answer | 0.0% [0.0%, 0.0%] | 50.0% [33.3%, 66.7%] | 0.0% [0.0%, 0.0%] |
| Evidence from the asked patent | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | – |
| Asked claim retrieved | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | – |
| Claim content in the answer | 66.2% [52.9%, 78.4%] | 1.7% [0.2%, 3.4%] | 2.3% [0.8%, 4.0%] |
| Statements supported by the patent | 64.7% [50.7%, 77.0%] | 20.0% [5.0%, 36.7%] | 20.3% [10.3%, 30.8%] |
| Statements contradicted/unsupported | 28.4% [16.6%, 41.7%] | 70.0% [46.7%, 93.3%] | 73.3% [61.7%, 85.6%] |
| Latency | 37,253 [31,992, 43,994] | 17,681 [14,371, 21,412] | 3,641 [3,447, 3,836] |
| Tokens | 3,058 [2,667, 3,477] | 2,747 [2,285, 3,258] | 152 [147, 157] |

*Mean [95% bootstrap CI] over questions.*

## Paired differences vs. live

| Variant | Metric | Δ mean [95% CI] | clear? |
|---|---|---|---|
| local_only | Said it could not answer | +50.0 pp [+33.3, +66.7] | yes |
| local_only | Evidence from the asked patent | -100.0 pp [-100.0, -100.0] | yes |
| local_only | Asked claim retrieved | -100.0 pp [-100.0, -100.0] | yes |
| local_only | Claim content in the answer | -64.6 pp [-76.3, -51.9] | yes |
| local_only | Statements supported by the patent | -39.0 pp [-59.0, -18.9] | yes |
| local_only | Statements contradicted/unsupported | +36.4 pp [+13.8, +58.7] | yes |
| local_only | Latency | -19571.3 [-27829.7, -12543.6] | yes |
| local_only | Tokens | -311.3 [-850.8, +245.8] | no |
| closed_book | Said it could not answer | +0.0 pp [+0.0, +0.0] | no |
| closed_book | Claim content in the answer | -63.9 pp [-76.2, -50.4] | yes |
| closed_book | Statements supported by the patent | -44.5 pp [-57.8, -30.6] | yes |
| closed_book | Statements contradicted/unsupported | +44.9 pp [+30.4, +59.5] | yes |
| closed_book | Latency | -33612.0 [-40280.5, -28357.9] | yes |
| closed_book | Tokens | -2906.6 [-3324.6, -2515.4] | yes |
