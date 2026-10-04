# Building the evaluation dataset

The numbers in the final report are only as good as this dataset. This guide explains how
to build it so that the results are fair, reproducible and defensible in a viva.

The format is shown by the working example in
[experiments/datasets/dev/dataset.yaml](../experiments/datasets/dev/dataset.yaml). **That dev set
is synthetic and was written by the AI coding assistant while building the framework. Use it
to test the pipeline, never as a reported result.**

> A draft over 16 real patents already exists: `experiments/datasets/real_v1/` (built with
> `backend/scripts/build_corpus.py`, questions and labels drafted by the AI assistant).
> Verifying it (step 4) is faster than starting from scratch; its `REVIEW.md` shows every
> question with the passages its labels point to.

## 1. Choose the corpus

- **Real patents, 2–3 technical domains**: for example battery thermal management, wireless
  charging and one other. Use 15–30 documents per domain. Download the PDFs (Google Patents,
  Espacenet), or import them through the app once the EPO keys work.
- **Include near neighbours.** Several patents in each domain should be about similar things,
  so that retrieval has to tell them apart. A corpus of unrelated documents makes retrieval
  look better than it is.
- Put the files in `experiments/datasets/<name>/corpus/` and list them under `corpus:`
  with short ids. To download public patents as clean text files with standard headings:
  `cd backend && .venv/bin/python -m scripts.build_corpus --out ../experiments/datasets/<name>/corpus US9178361B2 …`
  (granted US patents and US applications work; pages without English full text are skipped).

## 2. Write the questions (target 60–100)

Spread them over the item types, so that results can be broken down by type:

| type | example | what it tests |
|---|---|---|
| `lookup` | "At what temperature does the controller increase pump speed?" | one fact in one passage |
| `multi_passage` | "How is the core temperature estimated?" | combining 2–3 passages |
| `claim_explanation` | "What does claim 3 add?" (with `scope`) | direct section access, claim reading |
| `comparison` | "Compare how these two patents cool the cells." (`scope` with 2 docs) | balanced evidence, no cross-source mixing |
| `similar_search` | "Find patents similar to my battery patent." | external search (needs EPO keys) |
| `patent_lookup` | "What does EP1234567 claim?" | resolving numbers, fetching details |
| `unanswerable` | "What is the pack's charging power?" (not stated) | abstaining instead of inventing |
| `legal` | "Does A infringe B?" | refusing legal opinions, reframing as a technical comparison |

Rules:

- **Write questions before you look at any system output.** Questions shaped by what the
  system happens to answer well inflate the results.
- Use the vocabulary a user would use, not the patent's exact wording. Questions copied
  from the text make keyword search look unrealistically good.
- At least 15% of the questions should be unanswerable. Otherwise "always answer" looks
  like a good strategy.
- `scope:` means "the user selected these documents". Use it for claim and comparison
  questions, as a real user would.

## 3. Label the ground truth

For each question:

- **`relevant`**: every passage that answers it. Locate each one by *content*:
  - `{doc: battery, contains: "short exact quote"}`: 3–8 words copied from the passage.
    Keep the quote short, so that it still falls inside one chunk when the corpus is
    re-chunked with fixed-size windows (Experiment B).
  - `{doc: battery, claim: 3}`: a specific claim.
  - `{doc: battery, section: abstract}`: a whole section.

  If you give several conditions in one label, all of them must hold. Labels never use
  chunk IDs, because those change whenever the corpus is re-chunked. Claim and section
  labels also match passages that merely *contain the opening text* of that claim/section,
  because fixed-size chunks carry no claim or section information (otherwise Experiment B
  would be biased against them).
- **`key_facts`**: short strings that a correct answer must contain, such as `"10 Hz"` or
  `"thermistor"`. Matching is exact apart from case and spacing, so pick the patent's own
  terms.
- **`expected_intent`** and **`expected_tools`**: what a sensible agent *should* do (not
  what ours happens to do). These score Experiment H.
- **`legal: true`** for questions that ask for a legal opinion.

Run `make eval-review DATASET=experiments/datasets/<name>/dataset.yaml`. It checks that every
label matches a passage under both chunking strategies and that every key fact occurs in the
labelled documents, then writes `REVIEW.md`. Validation also rejects typos
(an unknown key such as `relevent` would otherwise silently drop the labels), unknown corpus
ids, and answerable questions without labels.

## 4. Two people, then freeze

**Label completeness.** In real patents the same fact usually appears in several places
(abstract, summary, a description paragraph, a claim). When verifying, search the patent
(Ctrl+F in the corpus .txt) for every passage that answers the question and add each one;
otherwise passage-level recall and MRR are underestimated. (Phase 10: with the draft labels
the baseline found a labelled passage for only 38% of questions, yet took passages from the
right patent for 92%.)

**Which set is which.** `real_v1` (AI-drafted, and already used to tune the agent in
Phase 10) is the **dev** set. Write the **test** questions yourselves, without looking at
system output, over the same corpus or additional patents.

- Each question is labelled by one team member and **checked by a second**. Write
  disagreements and how they were resolved in `notes:`.
- **Split dev / test.** Use about 20% of the questions (`dev`) to tune prompts, thresholds
  and rules. Report numbers only on the remaining 80% (`test`), which must not be looked at
  while tuning. The Phase 9 smoke run already showed why: two planner rules and one label
  were changed after seeing dev results. That is fine on dev and would be cheating on test.
- Once the test set is final, record its fingerprint (printed by `eval-validate`, and stored
  in every result's `summary.json`). If the fingerprint changes, earlier results are no
  longer comparable.

## 5. Human labels for the verifier (Experiment I)

See [labelling_guide.md](labelling_guide.md).
