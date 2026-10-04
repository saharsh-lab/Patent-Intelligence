# Verifier choice on a development/test split of the Experiment I labels

Labels: test_claims_A_labeled.csv (one team member, AI-assisted). Split by a hash of the statement id. The NLI + lexical rescue was designed on the development half only.

| Half | Method | n | Accuracy | κ | False alarms (labelled supported) | Unsupported caught |
|---|---|---|---|---|---|---|
| development | nli | 72 | 0.653 | 0.114 | 24/69 | 3/3 |
| development | nli_lexical | 72 | 0.833 | 0.25 | 11/69 | 3/3 |
| development | nli_llm | 72 | 0.917 | 0.217 | 4/69 | 1/3 |
| test | nli | 78 | 0.718 | 0.249 | 17/68 | 4/6 |
| test | nli_lexical | 78 | 0.744 | 0.278 | 15/68 | 4/6 |
| test | nli_llm | 78 | 0.885 | 0.356 | 2/68 | 3/6 |
| all | nli | 150 | 0.687 | 0.178 | 41/137 | 7/9 |
| all | nli_lexical | 150 | 0.787 | 0.275 | 26/137 | 7/9 |
| all | nli_llm | 150 | 0.893 | 0.29 | 7/137 | 3/9 |
