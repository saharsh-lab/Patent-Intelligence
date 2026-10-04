# Labelling answer statements (Experiment I)

Experiment I measures how often each automatic verifier (NLI, LLM judge, word overlap)
agrees with a **person** on whether an answer statement is supported by the passages it
cites. Every grounding score in the report depends on the verifier, so this is what makes
those scores trustworthy.

## Getting the file

```bash
make eval-export RESULT=experiments/results/exp_a_pipelines/<run>
# → experiments/labels/exp_a_pipelines_<run>.csv (a random sample of 150 statements)
```

Open it in Excel, Numbers or Google Sheets. Each row contains:

| column | meaning |
|---|---|
| `statement` | one sentence (or table cell) from a generated answer |
| `passages` | the passages that sentence cited, each starting with `Source: <document>, <section/claim>` |
| `human_verdict` | **you fill this in** |
| `notes` | optional: why, especially for hard cases |

The file deliberately leaves out the system's own verdict, so that you are not influenced
by it.

## The three verdicts

Judge **only against the passages shown**. Ignore your own knowledge and whether the
statement is true in the real world.

| verdict | write | when |
|---|---|---|
| supported | `s` | Everything the statement says is stated in, or directly implied by, the passages. Paraphrase is fine. |
| partially supported | `p` | Some of it is stated, but it adds a detail that is not (an extra number, component or purpose), or it overgeneralises ("always", "all"). |
| unsupported | `u` | The passages don't say it, say something different, or contradict it. Also use `u` if the statement attributes a feature to the wrong patent. |

Edge cases:

- **Numbers and units must match.** "below 40 °C" vs. a passage saying "below 45 degrees"
  is `u`.
- **Claim references.** "Claim 3 adds current limiting" is `s` if the cited passage is claim 3
  and says so. The `Source:` line tells you which claim a passage is.
- **Combined facts.** "The pack has a pump and a cold plate", where one passage gives the
  pump and another the cold plate, is `s`. Judge against all cited passages together.
- **Hedged statements** ("may", "can") are `s` when the passage says the same with the
  same hedge.
- If you can't decide, write `p` and explain in `notes`.

## Procedure

1. Two team members label the **same** file independently, saving their copies as
   `<file>_A.csv` and `<file>_B.csv`.
2. Compute the agreement between the two people (Cohen's κ). The same function the
   framework uses works: `app.evaluation.metrics.cohen_kappa`. Human-human agreement is
   the ceiling: no verifier can be expected to agree with people better than people agree
   with each other.
3. Discuss the disagreements and agree on a final verdict for each. Save the result as
   the file that `experiments/configs/exp_i_verifiers.yaml` points to.
4. Run `make eval-verifier`.

Report human-human κ next to each verifier's κ and accuracy.
