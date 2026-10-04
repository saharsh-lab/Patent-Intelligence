# Experiments

```
datasets/dev/                  20 questions, 3 SYNTHETIC documents (framework tests only)
datasets/real_v1/              54 questions, 16 REAL patents: DRAFT labels, needs team
                               verification (REVIEW.md lists every item with its passages)
datasets/<name>/dataset.yaml   labelled questions + corpus files  (docs/dataset_guide.md)
configs/*.yaml                 one file per experiment (which variants, which settings)
labels/*.csv                   human verdicts for Experiment I     (docs/labelling_guide.md)
results/<experiment>/<run>/    written by the runner; shown on the Evaluation page
```

## Running

```bash
make eval-dry CONFIG=experiments/configs/exp_a_pipelines.yaml   # validate only
make eval     CONFIG=experiments/configs/exp_a_pipelines.yaml   # run
make eval-rescore RESULT=experiments/results/<exp>/<run>      # after labels change
```

Any config can run on another dataset with `--dataset`:
`python -m app.evaluation run --config ../experiments/configs/exp_a_pipelines.yaml --dataset ../experiments/datasets/real_v1/dataset.yaml`

Every variant uses the settings in `.env`, overridden by the config. To run with local
models without editing `.env`, set environment variables for one run:

```bash
cd backend
LLM_PROVIDER=openai_compatible LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama \
LLM_MODEL=qwen3:8b LLM_REASONING_EFFORT=none EMBEDDING_PROVIDER=local VERIFIER_METHOD=nli \
.venv/bin/python -m app.evaluation run --config ../experiments/configs/exp_a_pipelines.yaml
```

Experiments use a separate database (`EVAL_DATABASE_URL`, created automatically). The
runner deletes and re-ingests the dataset's documents there, so only they can be
retrieved, and your own uploads are never touched.

## Each result folder

| file | contents |
|---|---|
| `config.yaml` | the config exactly as run |
| `environment.json` | package versions, dataset SHA-256, every variant's full settings (secrets removed) |
| `runs.jsonl` / `runs.csv` | one scored row per (variant, question, repeat), with the run id in the eval DB |
| `summary.json` | means, 95% bootstrap CIs, paired differences, per-type breakdown, threshold sweep |
| `report.md` | the same as tables, ready to paste into the report |

## Experiments

| ID | config | status |
|---|---|---|
| — | `smoke.yaml` | fake models; checks the framework in ~2 s |
| A | `exp_a_pipelines.yaml` | ready |
| B | `exp_b_chunking.yaml` | ready |
| C | `exp_c_topk.yaml` | ready |
| D | `exp_d_rerank.yaml` | ready (needs `make setup-ml`) |
| E | — | needs EPO credentials (single source vs. multi-source) |
| F | `exp_f_tool_selection.yaml` | ready (`AGENT_TOOL_POLICY=all` = every available tool) |
| G | `exp_g_verification.yaml` | ready |
| H | `exp_h_planner.yaml` | ready (needs a real LLM) |
| I | `exp_i_verifiers.yaml` | needs human labels |

Results on `datasets/dev` (synthetic) and on `real_v1` before verification are **not
research results**; every report built from them says so at the top.

## Verifying real_v1 (team)

1. `make eval-review DATASET=experiments/datasets/real_v1/dataset.yaml` → open
   `datasets/real_v1/REVIEW.md`; two people check every item and fix `dataset.yaml`.
2. Set `labelled_by` to your names (this removes the draft warning). `real_v1` stays the
   **dev** set (the agent was tuned on it); write the **test** questions independently.
3. Re-score earlier runs with `make eval-rescore`, or re-run the experiments.
