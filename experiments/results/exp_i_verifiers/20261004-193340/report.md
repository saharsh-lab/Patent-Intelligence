# exp_i_verifiers — 20261004-193340

150 labelled statements (test_claims_A_labeled.csv): supported 137, partially_supported 4, unsupported 9


| Method | Accuracy [95% CI] | Cohen's κ | Macro-F1 | Unsupported detection P / R / F1 | ms/claim |
|---|---|---|---|---|---|
| lexical | 0.760 [0.693, 0.827] | 0.238 | 0.471 | 0.40 / 0.44 / 0.42 | 0 |
| nli | 0.680 [0.607, 0.753] | 0.163 | 0.389 | 0.19 / 0.56 / 0.29 | 947 |
| llm_judge | 0.860 [0.800, 0.913] | 0.196 | 0.452 | 0.40 / 0.22 / 0.29 | 3710 |

Confusion matrix — lexical (rows: human, columns: verifier)

| human \ verifier | supported | partially_supported | unsupported |
|---|---|---|---|
| supported | 108 | 24 | 5 |
| partially_supported | 1 | 2 | 1 |
| unsupported | 2 | 3 | 4 |

Confusion matrix — nli (rows: human, columns: verifier)

| human \ verifier | supported | partially_supported | unsupported |
|---|---|---|---|
| supported | 96 | 22 | 19 |
| partially_supported | 1 | 1 | 2 |
| unsupported | 2 | 2 | 5 |

Confusion matrix — llm_judge (rows: human, columns: verifier)

| human \ verifier | supported | partially_supported | unsupported |
|---|---|---|---|
| supported | 126 | 8 | 3 |
| partially_supported | 3 | 1 | 0 |
| unsupported | 6 | 1 | 2 |
