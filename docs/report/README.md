# Report drafts

Chapter drafts for the project report, written to be pasted into the college template.
They describe the system as implemented; **results are placeholders** (`[RESULT: …]`)
until the final experiments run on the team-verified test set.

| File | Chapter | Status |
|---|---|---|
| 01_abstract.md | Abstract | draft; numbers to fill in |
| 02_introduction.md | Introduction, objectives, contributions | draft |
| 03_literature_review.md | Related work | draft; **verify every reference** |
| 04_system_design.md | Architecture and design | draft |
| 05_implementation.md | Implementation | draft |
| 06_evaluation_methodology.md | Dataset, metrics, experiments, statistics | draft |
| 07_results.md | Results | **template**: fill with generated tables |
| 08_discussion.md | Discussion, limitations, threats to validity | draft; revise after results |
| 09_conclusion.md | Conclusion and future work | draft; revise after results |
| references.md | Bibliography | **verify before submission** |

Figures: `docs/diagrams/*.png` (slides) and `*.svg` (report); sources `*.mmd`.
Tables: `cd backend && .venv/bin/python -m app.evaluation tables --result ../experiments/results/<exp>/<run> --format latex`.

Rules for the final text:
1. Every number comes from a result folder (cite the folder name in a footnote or appendix).
2. A difference is called a difference only when its 95% CI excludes zero (marked †).
3. Results on `dev` or on unverified (`DRAFT`) labels are never reported as findings.
