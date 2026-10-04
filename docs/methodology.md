# Research Methodology

> Status (Phase 9): the evaluation framework is built and every experiment below except E
> and F has a ready config in `experiments/configs/`. **No research results yet**: the only
> dataset is the synthetic, AI-written dev set, which only tests the framework.
> How to build the real dataset: [dataset_guide.md](dataset_guide.md).

## Research questions (provisional)

The final research claim is chosen **after** experiments, not before. Candidate questions:

- **RQ1.** Does an agent that *selects* sources and tools produce better-grounded patent
  answers than a fixed single-source RAG pipeline, and at what latency/cost?
- **RQ2.** How much does claim-level verification (with re-retrieval) reduce
  unsupported statements compared with generation alone?
- **RQ3.** Which retrieval design choices (chunking, top-k, hybrid vs. vector-only,
  reranking) matter most for patent text?

## Experiments (as run, 2026-10-04; results in docs/report/07_results.md)

| ID | Comparison | Held constant |
|---|---|---|
| A | Baseline RAG vs. agentic RAG | LLM, embedding model, dataset |
| B | Chunking: section-aware (one passage per claim) vs. fixed-size windows | Retrieval method, top-k |
| C | Passages given to the LLM: k ∈ {3, 6, 10} | Everything else |
| D | Without vs. with cross-encoder reranking | Candidate pool size (30) |
| E | New (2026) patents: agent with live EPO vs. local documents only vs. LLM alone; generated question set (`live-build`, `live-run`) | LLM |
| F | Agent with tool selection vs. fixed "call every tool" pipeline | Tools available |
| H | Rules planner vs. LLM planner (`AGENT_PLANNER`) | Everything else; measures tool-selection accuracy, invalid-output rate, cost |
| G | Generation only vs. + claim verification vs. + verification & regeneration (`VERIFY_MODE`) | Retrieval |
| I | Verifier method: NLI vs. LLM judge vs. lexical (`VERIFIER_METHOD`), scored against human labels | Answers being verified |

## Reproducibility

- Every answer is an `agent_runs` row whose `config` stores model names, top-k,
  reranker setting, chunking strategy, and prompt version.
- Experiment configs live in `experiments/configs/*.yaml`. Results are written to
  `experiments/results/<experiment>/<timestamp>/` (summary, CSV, Markdown report, settings
  and package versions, dataset fingerprint) and to the `evaluations` table of the
  separate evaluation database.
- Questions are the unit of analysis: repeats are averaged per question, means get 95%
  bootstrap confidence intervals, and variants are compared with paired bootstrap
  differences. A difference is only claimed when its interval excludes zero.
- The LLM temperature is 0 for experiments; repeated runs measure remaining variance.
- **Timing protocol:** variants that share an index run interleaved (each question with
  every variant before the next question) and counterbalanced (the variant that goes first
  rotates, because the LLM server reuses the previous prompt's cache), one untimed warm-up
  question per variant loads the models, and reported runs use an otherwise idle machine. Report median (p50) and p95
  latency next to the mean.
- External API responses are cached, so re-runs use identical evidence.

## Dataset

Format and procedure: [dataset_guide.md](dataset_guide.md). Target: 60–100 questions over
real patents in 2–3 technical domains, with near-neighbour documents. Types: lookup,
multi-passage, claim explanation, comparison, similar-patent search, patent lookup,
unanswerable and legal. Every question is labelled by one team member and checked by a
second; the dataset is split into dev (tuning) and test (reporting), and the test split is
frozen (SHA-256 fingerprint) before any reported run.

Human verdicts for Experiment I: [labelling_guide.md](labelling_guide.md). Two labellers;
report their agreement (κ) as the ceiling for the verifiers.

## Threats to validity (to address in the report)

- **Small n.** With 60–100 questions, only large differences will be clear; report CIs.
- **Labels written by the developers.** Mitigated by the second-person check and by writing
  questions before seeing outputs.
- **One LLM.** Results may not transfer to other models; fix one model for all reported runs.
- **Verifier-dependent metrics.** Grounding scores are only as good as the verifier;
  Experiment I measures that.
- **Key-fact recall** misses paraphrases, so it underestimates correctness.
- **Chunk size vs. retrieval metrics.** Bigger chunks are "relevant" more easily. Report
  context tokens and grounding next to recall/MRR in Experiment B, and compare chunkings at
  a similar context budget.
- **Draft labels.** `real_v1` was drafted by the AI assistant; every result on it carries a
  warning until two team members verify the labels.
- **`real_v1` is a dev set.** The system was tuned after looking at results on it (Phase 10:
  the planner's similar-search guard). Reported numbers must come from test questions the
  team writes independently, over the same corpus or new patents.
- **Incomplete passage labels.** Real patents repeat each point in the abstract, summary,
  description and claims. Passage-level recall/MRR undercount relevance when labels list
  only one or two passages, so report the document-level metrics ("right sources found",
  "passages from right sources") next to them.
