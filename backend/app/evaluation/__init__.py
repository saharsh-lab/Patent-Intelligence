"""Evaluation framework (Phase 9): labelled questions → runs → metrics → reports.

    dataset.py       question set format + "is this passage relevant?" matching
    metrics.py       metric formulas and statistics (pure functions, no database)
    scoring.py       turns one stored run into a row of metric values
    config.py        experiment configs (YAML) and per-variant settings
    runner.py        answers every question with every variant and writes results;
                     rescore() re-scores stored runs after labels change
    verifier_eval.py exports claims for human labelling; scores verifiers against labels
    results.py       reads result folders (for the API / Evaluation page)

Command line: `python -m app.evaluation --help`.
"""
