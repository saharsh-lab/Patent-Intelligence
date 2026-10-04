# Observations Log

Dated, qualitative observations made while building the system. These are **not
experimental results**: they come from a handful of manual queries on two synthetic
documents. They are recorded because some suggest hypotheses worth testing properly
in Phases 9–10, and because they explain design decisions.

Setup unless stated: BGE-M3 embeddings, hybrid retrieval (top-6), Qwen3-8B via Ollama
(`reasoning_effort=none`, temperature 0), synthetic fixtures `battery_patent.txt` and
`wireless_patent.txt`.

---

### 2026-10-03 — Patent paragraph numbers caused fabricated citation labels

**Seen:** Asked "How does the system estimate the core temperature of a cell?", the
model cited `[E11]`, `[E12]`, `[E13]`, but only `[E1]`–`[E6]` existed. The facts in those
sentences came from paragraphs numbered `[0011]` and `[0013]` inside passage E1.
Citation coverage: 0.20 (4 of 5 sentences had only invalid labels).

**Interpretation:** The model confused the patent's own paragraph numbers with our
evidence labels, because both use the `[...]` bracket form.

**Change:** Prompt v2 rewrites `[0011]` as `¶0011` inside evidence. On the same
question: coverage 1.00, no invalid citations.

**Hypothesis for later:** Domain-specific bracket conventions in patents (paragraph
numbers, reference numerals) raise citation-label hallucination. Testable by comparing
prompt v1 and v2 on the evaluation set.

### 2026-10-03 — Retrieval-level gate avoids LLM calls for off-topic questions

**Seen:** "What is the capital of France?" had best BGE-M3 similarity 0.27, below the
0.35 threshold, so it was answered "insufficient evidence" in 126 ms with no LLM call.
"Who is the assignee of the battery patent and when was it filed?" passed the gate
(similarity 0.45, because it is on-topic), and the LLM itself replied
`INSUFFICIENT_EVIDENCE`.

**Note:** The 0.35 threshold is a guess from a few queries. It must be calibrated on
the evaluation set (Phase 9), measuring both false refusals and false answers.

### 2026-10-03 — Cited sentences can still contain unsupported interpretation

**Seen:** For "What does claim 3 add to claim 1?", the sentence "This enhancement
introduces a safety mechanism to prevent overheating by dynamically adjusting the
charging current…" cites `[E1]`, but "safety mechanism" and "dynamically adjusting"
are the model's interpretation, not text in claim 3.

**Implication:** Citation coverage overstates grounding. Claim-level verification
(Phase 8) is needed to check whether the cited passage actually supports the statement.

### 2026-10-03 — Short title chunks rank highly

**Seen:** Title-only chunks (8 tokens) appear in the top results for broad questions
(e.g. overheating question, rank 1 in vector search). A small MS-MARCO cross-encoder
(MiniLM-L6) also ranked the title above the passage that actually answers the question.

**To test:** Effect of the BGE reranker (Experiment D) and of excluding or merging
very short chunks (Experiment B variant).

### 2026-10-03 — EPO OPS rejects anonymous requests

**Seen:** An unauthenticated search request to `ops.epo.org/3.2` returned HTTP 403 with
header `X-Rejection-Reason: AnonymousQuotaPerDay` and an XML error body, even with
`Accept: application/json`. The client therefore reads that header to explain quota
errors and never assumes error bodies are JSON. Registered credentials are required.

### 2026-10-03 — Agent: picking the wrong "my invention"

**Seen:** "Find patents similar to my battery thermal management invention" with two
uploaded documents. The first version used the most recently uploaded document (a
wireless charger), extracted the concepts "Quality Factor Detection", and searched for
the wrong invention. **Change:** resolve the subject by title overlap with the question,
restrict "my …" to uploaded documents, and refuse to guess when ambiguous. After the
change the battery document was chosen and the search used "Thermal Model Cooling".

### 2026-10-03 — Cited but unsupported statement (hallucination with a real citation)

**Seen:** "Does my battery patent infringe XX0000001A1?" when the agent had failed to
include the user's document. The answer stated "Both the patent and the user's battery
patent involve thermistors…" citing [E4][E3], passages that describe only XX0000001A1.
Citation validity checks passed; the claim was still unsupported. **Implication:**
claim-level verification (Phase 8) is necessary; citation checks alone are not.

### 2026-10-03 — Qwen3 planner output outside the allowed schema

**Seen:** Asked to classify intent, Qwen3 returned `"intent": "legal_question"` (not an
allowed value) with otherwise useful fields. **Change:** keep valid fields, take the
intent from rules (`analyzer = llm_rules_intent`). Worth measuring: how often the
planner output is invalid per model, and the effect of rules vs. LLM planning on
tool-selection accuracy (candidate experiment).

### 2026-10-03 — Legal questions: refusal vs. useful technical answer

**Seen:** With the user's legal question passed verbatim plus a "no legal opinions"
instruction, Qwen3 replied only `INSUFFICIENT_EVIDENCE` (safe but unhelpful). Reframing
the generation question as "describe and compare the technical features" (original
question kept in the run record, disclaimer shown in the UI) produced a disclaimer
followed by a cited technical comparison.

### 2026-10-03 — Comparison: right source, valid citation, wrong content

**Seen:** LLM comparison (Qwen3) of the battery document with XX0000001A1 and
XX0000003A1, run twice. Every citation metric was clean (100 % cells cited, 0
cross-source, 0 fabricated), yet the cell "Problem addressed" for XX0000001A1 stated
"Conventional systems cannot detect hot spots in individual cells" citing a passage of
XX0000001A1 that says nothing of the kind. The sentence comes from the *battery
document's* background. **Implication:** the model mixes content across sources even
when its citations are structurally valid. This is the clearest case so far for
claim-level verification (Phase 8), and a good test item for it.

### 2026-10-03 — Comparison cost: LLM vs. extractive

**Seen (3 sources, local Qwen3-8B):** LLM mode 31–53 s, ~1.2k prompt / ~0.8k output
tokens; extractive mode 0.7 s, no LLM. Extractive cells are faithful by construction
but sometimes pick unhelpful passages (e.g. a claim for "problem addressed" when no
background exists; now "not stated" instead). Candidate experiment: human-rated
usefulness vs. faithfulness of the two modes.

### 2026-10-03 — Flaky vector-search test (engineering note)

**Seen:** A Phase 1 vector-search test failed intermittently after many test runs.
Cause: every test inserts rows and rolls back; rolled-back rows leave dead entries in
the HNSW index until VACUUM, degrading approximate search in the test database.
**Change:** VACUUM the `chunks` table at the start of each test session. Separately,
pgvector iterative index scans are enabled for filtered vector queries as a recommended
safeguard (not shown to change results at current data sizes).

### 2026-10-04 — NLI verifier catches the earlier misattribution

**Seen:** The Phase 7 "hot spots" cell (content from the battery document, cited to
XX0000001A1's passage) was flagged by the NLI verifier as "supported by E2, which it did
not cite": E2 is the battery document's background. Also caught in an agent answer: "claim
1 … describes … cells immersed in a dielectric fluid" (that feature belongs to
XX0000003A1, not the battery patent's claim 1).

### 2026-10-04 — Verifier false alarms and two fixes

**Seen:** (1) "Claim 3 adds X" judged unsupported against the passage "3. The system of
claim 1, wherein X" (entailment 0.01): NLI did not know the passage *is* claim 3.
(2) "Thermistors, coolant pump, controller, cold plate" combines two cited passages;
each alone does not entail it. **Changes:** prefix each premise with its location
("Source: battery_patent.txt, claim 3."); also test a claim against all its cited
passages joined. After: the claim-3 statement became supported; the list became
partly supported. **Remaining:** "a metallic foreign object, such as a coin, can absorb
energy and become dangerously hot" vs. "Metal objects … absorb energy … can become
dangerously hot" was judged unsupported (the coin example comes from another passage).
The xsmall NLI model is strict. Verifier precision/recall must be measured against
human labels (Phase 9); a larger NLI model is a one-setting change.

### 2026-10-04 — Regeneration: helps sometimes, not always

**Seen (Qwen3, NLI):** "How does the wireless charger detect a coin?": attempt 1 grounding
0.10 → regenerated with feedback and extra passages → 0.75 (kept). "What does claim 3 add
to claim 1?": 0.50 → regenerated → 0.00 (discarded; original kept). Remaining unsupported
sentences were mostly the model's own commentary ("…improving safety and efficiency")
outside the Interpretation paragraph. **To measure (Experiment G):** average grounding,
latency and cost for verify-off vs. report vs. regenerate.

### 2026-10-04 — Phase 9 smoke run finds two planner gaps and one wrong label

**Seen (fake models, dev set):** "Compare how these two documents cool the battery
cells." (two documents selected) was answered as ordinary Q&A: the rule for "this/my
document" did not cover "these two documents". A legal question about two selected
documents ("Does the immersion cooling document infringe claim 1 of the battery
patent?") was not turned into a technical comparison, because that rule only fired when
publication numbers were typed. **Changes:** plural scope references; in
`resolve_targets`, 2+ documents in scope plus comparison wording or a legal question →
compare. Intent accuracy on dev went from 90% to 100%. **Label revised:** q04 names the
"background" section, so reading that section directly is a correct tool choice; the
label was too narrow. **Caveat:** tuning on these questions is why they are *dev*
questions; reported numbers must come from a separate test split.

### 2026-10-04 — The NLI verifier was too strict on multi-sentence passages (bug)

**Seen (Experiment A on dev, Qwen3 + BGE-M3 + NLI):** the baseline's answer to q01 was
"The controller samples every thermistor at 10 Hz [E1]" (all key facts present), but its
grounding was 0.00 (entailment p=0.02). The same statement scored p=0.99 against that
sentence alone, and p=0.04–0.38 against its three-sentence paragraph. The xsmall NLI
model, trained on short single-sentence premises, loses entailment as unrelated
sentences are added. Most of the Phase 8 "false alarms" were this effect, not only
strictness. **Change:** score each statement against every sentence and every pair of
neighbouring sentences of the passage (plus the whole passage), with the "Source:" line
kept on each, and take the maximum entailment (the SummaC approach, Laban et al. 2022).
Claim elements separated by ";" count as sentences. **After:** q01's statement p=0.99; "Claim 1 requires a
temperature sensor attached to each battery cell" vs. the full claim 1, p=0.99; a
wrong frequency (50 Hz) and an invented component are still caught (contradiction
p=1.00). About 0.25 s for 4 checks. The interrupted run (baseline half, old verifier) is
kept outside the results folder for comparison. **Lesson:** the verifier itself must be
evaluated (Experiment I) before any grounding number is reported. Without a labelled
evaluation run, this bug would have silently lowered every grounding score.

### 2026-10-04 — LLM planner: wrong refusals and invented sections (fixed)

**Seen (Experiment A on dev, Qwen3 as planner):** intent accuracy 90%, but tool-set exact
match only 55%. (1) "What happens when a cell's estimated core temperature rises faster
than 2 °C per minute?" was classified *out of scope*, so the agent refused without
searching (a wrong abstention). (2) For 7 ordinary questions the LLM set a section
("description") that the question never named, so the agent read that section instead of
searching, and on q02 it missed the answer (hit@k 0 vs. 1 for the baseline). (3) One
unanswerable question was treated as "find similar patents". **Changes:** the LLM's
"out of scope" no longer stops the agent (refusals now come from the evidence gate);
sections and claim numbers are taken only when the question names them (as was already
the rule for publication numbers). The first Experiment A result is kept as the "before"
for this change. (3) is left for Experiment H to measure.

### 2026-10-04 — Pilot check of the verifier (NOT a result: 14 statements, AI-labelled)

**Seen:** to test the Experiment I tooling, 14 exported statements were labelled by the AI
assistant (kept outside `experiments/`). NLI detected both unsupported statements, but
(1) called "Both systems use coolant to manage battery temperatures" *contradicted*
(p=0.97–0.99): it is checked against each system's passage separately, and no sentence
window combines sentences from two passages; (2) never output "partially supported":
after taking the maximum over sentence windows, scores are near 0 or near 1. **Implication:**
comparison statements ("both", "unlike") are likely to get systematic false alarms;
Experiment I with real human labels must report per-type errors. Possible fix to test
then: for statements citing several passages, add windows that pair the best sentence of
each cited passage.

**After the planner guards (same dev questions, re-run):** agent tool-set exact match
55% → 95%, hit@k 88% → 100%, answer/abstain correct 95% → 100%, grounding 70.8% → 84.1%
(baseline 76.7% in both runs: its quality metrics were identical across the two runs at
temperature 0). Mean latency: agent 10.0 s vs. baseline 4.7 s. These are dev questions the
fixes were tuned on, so they show that the fixes work, **not** that the agent is better.

### 2026-10-04 — Claim/section labels were biased against fixed-size chunking (bug)

**Seen (Experiment B rehearsal, dev set, Qwen3 + BGE-M3):** fixed-size chunking appeared
much worse than section-aware chunking (recall@k 55% vs. 86%, hit@k 71% vs. 100%).
Cause: labels such as `{doc: battery, claim: 3}` were matched on chunk *metadata*
(claim number, section), which fixed-size chunks never carry, so they could never count
as relevant. **Change:** claim and section labels also carry an *anchor*, the first
~150 characters of that claim/section (shorter than the 60-token chunk overlap, so always
inside one fixed chunk); a passage is relevant if it has the metadata **or** contains the
anchor. A `rescore` command re-scored the stored runs without calling the model.
**After:** fixed chunking recall@k 100%, MRR 0.93 (section-aware 86%, 0.74). **But:** on
these short synthetic documents a 400-token fixed chunk covers most of a document, so it
is "relevant" almost by construction. Retrieval metrics alone favour big chunks. Grounding
went the other way (fixed 52% vs. section-aware 77%). **For the real Experiment B:**
report context tokens and grounding next to recall, and compare at similar context size.
`validate --check-labels` now checks every label under both chunkings.

### 2026-10-04 — Rehearsal of Experiments B–H on the dev set (NOT results: synthetic data)

Purpose: find problems before the real runs. What the rehearsal showed:

- **Everything runs end to end** with Qwen3 + BGE-M3 + NLI (+ BGE reranker for D): 6
  experiments, 260 runs, 0 failures, about 42 minutes.
- **Latency was confounded by run order (fixed).** In Experiment G, verification *off*
  looked slower than *report* (11.1 s vs. 8.4 s). Two of its runs took 30–34 s instead of
  3–4 s; the LLM needed 14.9 s for 65 tokens while other work (tests, label checks) ran on
  the same laptop. Because variants ran one after another, such slow spells biased
  whichever variant was running. **Changes:** variants that share an index now run
  interleaved (question 1 with every variant, then question 2, ...); one untimed warm-up
  question per variant loads the models first; the LLM planner's call is now timed
  ("0. analyze"; it was missing from the breakdown). **Protocol:** run reported
  experiments on an otherwise idle machine, and report median latency next to the mean.
- **The reranker works but is expensive here:** for a known question the relevant passage
  scored 0.82 and moved to rank 1; MRR 0.74 → 0.78 (not clear on 17 questions); latency
  +6 s per question on this laptop.
- **Experiment F behaves as designed:** "all tools" ran extra tools (tool-set exact 95% →
  60%, more tokens and LLM calls) without changing answer quality on this small set.
- **Experiment G:** regeneration on 24% of answers; grounding 79% (report) → 84%
  (regenerate), not a clear difference on 17 questions.
- **Experiment H:** after the Phase 9 guards, the LLM planner matched the rules planner on
  quality but cost one more LLM call (+1.6 s) per question. On this dev set the rules
  were also tuned, so this comparison needs the real test split.
- **Experiment C:** top-k 10 lowered grounding (61% vs. 77% at k = 6); more passages give
  the model more to mix up. To be checked on real data.

### 2026-10-04 — First run on real patents (real_v1 draft, Experiment A; NOT a result)

**Setup:** 16 real patents (~1,000 passages), 54 AI-drafted questions, Qwen3 + BGE-M3 + NLI,
variants interleaved. 108 runs, 0 failures; median latency ~15–19 s, because real passages
give 2,500–3,000-token prompts.

**Seen:**
1. **Passage labels were too narrow.** The baseline's hit@5 was only 38% (agent 64%), yet
   both took passages from the right patent for 92–94% of questions. In two inspected
   "misses" the retrieved passages did answer the question; the label only listed the
   abstract. **Changes:** document-level metrics ("right sources found", "passages from
   right sources"); the dataset guide now requires searching each patent for every
   answering passage. The agent's passage-level advantage is partly an artefact: its
   direct claim retrieval returns exactly the labelled claim passages.
2. **The LLM planner sent 7 plain lookups to similar-patent search** ("Which kinds of pumps
   can be used…?"), and the agent then abstained (no patent database configured): 6
   wrong abstentions. This never happened on the dev set. **Change:** find_similar is
   accepted from the LLM only with similarity wording ("like", "similar", "prior art",
   "patents", …). Re-run of those 7 questions: all 5 answerable ones answered (grounding
   0.5–1.0), both unanswerable ones still abstained.
3. **Prompt-cache order effect.** With interleaving, the second variant on the same
   question was up to 40% faster (46.7 s vs. 27.5 s for identical answers): the LLM server
   reuses the previous prompt's cache. **Change:** the variant that goes first now rotates
   per question. The run above predates this, so its latency comparison favours the agent.
4. **Consequence for the methodology:** real_v1 has now been used for tuning, so it is a
   dev set; the team must write the test questions independently.
