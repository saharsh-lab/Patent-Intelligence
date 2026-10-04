# Frozen live question set (Experiment E)

- **Built:** 2026-10-04 with `python -m app.evaluation live-build --config ../experiments/configs/exp_e_live.yaml`,
  live from EPO Open Patent Services, before any system run on it.
- **Contents:** 30 questions (claim 1 and one dependent claim each) about 15 EP/WO patents
  published 2026-04-15 to 2026-09-30, i.e. after the LLM's training data. Three topics:
  wireless charging foreign object detection, battery thermal management, immersion cooling.
- **Ground truth:** the claim text and abstract exactly as EPO supplied them, stored in
  `questions.json`. Nothing was written or labelled by hand.
- **SHA-256:** `2763406f60edcfc140da374a72acf0fc7f790cde535e81d847144a2cbd5d0533`
- Selection rules (automatic): EP or WO publication, English claims, a dependent claim with
  a "wherein" feature of at least 4 content words; claim headings and cancelled claims
  skipped.
