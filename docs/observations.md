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

### 2026-10-04 — First contact with the live EPO OPS service

**Seen:** with real credentials, the EPO client worked on the first attempt: OAuth token,
CQL search ("wireless charging foreign object detection": 212 results, newest published
2026-09-30), bibliographic data, claims (8,489 characters) and description (51,063
characters) for EP4815257A1; importing it produced 63 passages with all sections detected
and one passage per claim (26). The real responses are recorded in
`tests/fixtures/epo/recorded_*.json` and parsed by the test suite (the formerly skipped
test now runs), so a future change in EPO's response format shows up as a failing test.

### 2026-10-04 — Experiment F (tool selection) on the frozen test set: what the numbers hide

**Result (draft labels, not reportable yet):** choosing tools per question vs. calling
every tool gave the same answers (key facts, abstention, grounding: no clear difference)
with cleaner context: passages from the right sources +8.7 points (clear, 11 wins / 0
losses), context precision +1.6 points (clear), and fewer LLM calls (2.4 vs 2.7) and tokens.
Latency did not differ (p50 28.0 s vs 27.9 s).

**Inspected the 4 "intent errors" (92.5% intent accuracy):**
1. **n01, n03, n04: a labelling convention, not an error.** The questions name a patent
   ("claim 1 of US20190315232A1") that is already in the uploaded corpus. The agent
   resolved the number to the uploaded document and labelled the intent `document_qa`; the
   answer key expects `patent_lookup`. The tools used were exactly the expected ones and
   the right claim was retrieved in all three. Report intent accuracy with this caveat
   (49/53 strict; 52/53 counting these as correct). The test set is frozen, so the labels
   stay as they are.
2. **n04 key fact "missed": a strict string match.** The answer says "estimate the
   temperature at arrival of the battery"; the key fact is "estimated temperature at
   arrival". Key-fact recall is a normalised substring match, so it under-counts
   paraphrases. Mention this as a limitation of the metric (it is conservative).
3. **u04: a real failure, false premise.** "Which neural network does the Kalman filter
   battery patent train on cell temperatures?" The patent uses an extended Kalman filter
   and no neural network. The system did not reject the premise: it answered about the EKF
   ("trains on cell temperatures using an extended Kalman filter"). It never invented a
   neural network, and verification marked most of the answer unsupported (grounding 0.4),
   but it should have said the patent describes no neural network. **Limitation /
   future work:** a premise check before answering ("does the evidence mention the thing
   the question presupposes?"). Not changed now, so the measured system stays the one
   described in the report.

### 2026-10-04 — Experiments H, B, C, D on the frozen test set (draft labels)

All 477 runs succeeded. Points to keep in mind when writing them up:

1. **H (rules vs LLM planner):** the LLM planner was no better and is clearly worse on
   intent (4 losses, 0 wins), costs one extra LLM call (+318 tokens) and +2.4 s at the
   median. Supports keeping the rules planner as default.
2. **B (section-aware vs fixed chunks): read the precision carefully.** Fixed windows
   score slightly *higher* precision@k (+3.4 points, clear), but part of this is an
   artefact: windows are 400 tokens with 60 overlapping, so two neighbouring windows can
   both contain the opening of the same labelled claim and both count as relevant (5
   questions had more than one matching passage vs 1 for section-aware). The answer-side
   result is large and clear: grounding −18.5 points with fixed chunks (25 losses / 10
   wins), more invalid citations, +751 tokens and +5.3 s per answer.
3. **C (top-k):** more passages raise recall (k10: context recall +12.8 points) and k6
   improves key facts (+9.5) and grounding (+6.2), but dilute the context (passages from
   the right sources −6 to −12 points) and cost +4–6 s. A trade-off, no single winner.
4. **D (reranker):** the largest retrieval effect of all experiments: MRR +0.26, recall
   +14.5 points, key-fact recall +17.6 points, at +15 s per answer (p50 24 s → 42 s on a
   laptop CPU). Worth stating as "best quality, at a latency cost".

### 2026-10-04 — Invention self-check on 16 patents

**Seen:** first run (`selfcheck_invention/20261004-174507`) checked 15 of 16 patents:
US20220115917A1 was skipped because its claims 1–14 are "(canceled)" (a continuation;
claim 15 is the first real claim). **Change:** the self-check now takes the first claim
that is neither cancelled nor dependent ("of claim N"); test added. Re-run
(`20261004-175038`, the one to report): 16/16 found themselves first, all own features
disclosed, nearest other document always same-domain, top-3 same-domain 92.7%, 7.7 s per
analysis. The 15-patent run is kept for the record but superseded.

### 2026-10-04 — Final checks: Docker, browser, tests

- **Docker** (rebuilt, run on isolated databases): migrations of both databases, register →
  401 before login, upload into a chat, answer, live EPO search from inside the container,
  second user sees nothing of the first, no secrets in the web container. All passed.
- **Browser pass over every page** (production build): 13/13 steps passed, but the
  Evaluation page **crashed** once a self-check result existed: the page knew only
  experiment and verifier results and sent the self-check to the experiment view. Fixed:
  a self-check view, the right rows file in the API, and an "unknown result type" notice
  instead of a crash for any future kind.
- **Two tests failed after the EPO keys were added to `.env`:** tests read the developer's
  `.env`, so real credentials changed which code ran. Test setup now blanks all patent
  credentials (tests can never reach live services). The second failure exposed a real
  ordering bug: all hits from one watch check share a timestamp, so their order was
  arbitrary; hits are now ordered by check, then similarity (the import order), which
  also fixes the order shown on the Patent watch page. 354 backend tests pass.

### 2026-10-04 — Correction: which planner the agent used; label audit; rescoring

1. **The agent in Experiments A, F and G used the LLM planner**, not the rules planner:
   `.env` has `AGENT_PLANNER=auto`, which picks the LLM planner whenever a real LLM is
   configured (recorded in each variant's `run_config.agent.planner`). The earlier note on
   Experiment F was wrong to call the 3 patent-number "intent errors" a labelling
   convention: they are the LLM planner's choices. Experiment H shows the rules planner
   gets all 53 intents right (LLM planner 92.5%, 4 losses / 0 wins), with one LLM call
   fewer per question and no loss in answer quality. The default was not changed after
   seeing test results; the report states which planner each experiment used.
2. **Label audit by the assistant** (the team asked for it; not a human check): 4 key facts
   corrected (t03, t13, m02, n04), 2 notes added; details in FROZEN.md and item notes.
   All stored runs were re-scored, not re-run. Key-fact recall moved by at most +2.7
   points, about equally for both variants of every experiment; no conclusion changed
   except one: **the reranker's key-fact gain (D) is +15.4 points but no longer clear**
   (its CI now includes 0), whereas its retrieval gains (recall, MRR) stay clear.

### 2026-10-04 — Experiment I on the test-set statements

150 statements from the final Experiment A answers, labelled by one team member with an
AI assistant's help (no second annotator): 137 supported, 4 partial, 9 unsupported.
Result `exp_i_verifiers/20261004-193340`: accuracy lexical 0.76 / NLI 0.68 / LLM judge
0.86; κ 0.24 / 0.16 / 0.20; unsupported recall 4/9, 5/9, 2/9. Always answering
"supported" would score 0.913, so accuracy is misleading on these skewed labels.

**What it means:** the deployed NLI verifier is strict. It flagged 41 of 137
labelled-supported statements (30%) as partial or unsupported, so the system's grounding
scores (~70%) understate support relative to these labels (91%). Comparisons between
variants are unaffected (same verifier for all). With only 9 unsupported statements,
differences between methods are not reliable. Follow-ups (future work): a second
independent annotator, a larger sample with more unsupported statements, and calibrating
the NLI threshold on such labels.

### 2026-10-04 — Experiment E built: live data on brand-new patents

The question set is generated, not written: EPO is searched for EP/WO publications from
2026 (after the LLM's training data) in the three topics; for each, claim 1 and a
dependent claim become questions, and their EPO claim text is the ground truth
(`experiments/datasets/live_epo_v1/`, frozen before any run). Building it exposed parser
cases the importer never met: claim lists that start with a heading ("1. CLAIMS What is
claimed is:", "Attorney Docket No.: … What is claimed is:"), cancelled ranges ("3.-4.
(canceled)"), an independent claim ending in "wherein …", WO publications whose claims
EPO supplies only in Chinese or Japanese, and US publications without full text in OPS.
The patent search gained an office filter (`(pn=EP or pn=WO)` in CQL), without which
most hits were Chinese publications without English claims.

### 2026-10-04 — Experiment E results, and a misattribution bug it exposed

Run `exp_e_live/20261004-143512` (30 questions, 15 patents from 2026, 90 answers, none
failed): live retrieved the asked patent and claim 30/30, claim content 66%, 65% of
statements supported by the patent; the LLM alone never said it did not know (0/30),
claim content 2%, 73% of statements unsupported (e.g. EP4815257A1, wireless charging
object detection, described as "a photovoltaic system").

**Bug found:** without a patent source, the agent answered 15/30 questions by falling back
to a search of all local documents and attributing a local patent's claim to the asked
one ("Claim 2 of EP4815257A1 adds … electronic expansion valve … chiller", which is claim
2 of US20230415612A1). Statement verification cannot catch this: every sentence matches
its cited passage; only the named patent is wrong. **Fix:** a question naming a patent that
is neither indexed nor retrievable now ends with "<number> is not in your library and
could not be retrieved from a patent database"; regression test
`test_unavailable_patent_number_is_never_answered_from_other_documents` (fails without
the fix). Re-run of local_only only (`20261004-150821`): 30/30 declined, 2.5 s each. The
main experiments A–H are unaffected: every patent number in the test set is in the
corpus.
