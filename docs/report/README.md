# Report drafts

Chapter drafts for the project report, written to be pasted into the college template.
They describe the system as implemented. Results are filled in from the final test-set
runs (2026-10-04), whose labels are AI-written and AI-audited, not human-verified; this
limitation is stated in the abstract, methodology, results and discussion.

| File | Chapter | Status |
|---|---|---|
| 01_abstract.md | Abstract | draft; numbers to fill in |
| 02_introduction.md | Introduction, objectives, contributions | draft |
| 03_literature_review.md | Related work | references verified; add works the guide recommends |
| 04_system_design.md | Architecture and design | draft |
| 05_implementation.md | Implementation | draft |
| 06_evaluation_methodology.md | Dataset, metrics, experiments, statistics | draft |
| 07_results.md | Results | filled from generated tables (regenerate after any re-scoring) |
| 08_discussion.md | Discussion, limitations, threats to validity | draft with results |
| 09_conclusion.md | Conclusion and future work | draft with results |
| references.md | Bibliography | verified against the original publications (2026-10-04) |

Figures: `docs/diagrams/*.png` (slides) and `*.svg` (report); sources `*.mmd`.
Tables: `cd backend && .venv/bin/python -m app.evaluation tables --result ../experiments/results/<exp>/<run> --format latex`.

Rules for the final text:
1. Every number comes from a result folder (cite the folder name in a footnote or appendix).
2. A difference is called a difference only when its 95% CI excludes zero (marked †).
3. Results on `dev` or on `DRAFT` labels are never reported as findings. Results on the
   AI-audited test labels are reported only together with that limitation.

**One Word file:** `Project_Report.docx` (title page, all chapters, tables, figures,
references), built from these chapters by
`cd backend && .venv/bin/python scripts/build_report_docx.py`. Re-run it after editing a
chapter, then paste into the college template (fill in team members on the title page).
