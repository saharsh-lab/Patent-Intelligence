# 7. Discussion

## 7.1 Interpretation
**RQ1 (agent vs. baseline).** The agent retrieves the labelled passages more often and
higher in the ranking, and its answers are better grounded (6.1). The gain is not uniform:
it comes from questions where *routing* matters, namely claim and patent-number questions
(fetching the named claim directly instead of searching by similarity), comparisons
(evidence from each selected patent separately, so neither dominates) and legal-opinion
questions (recognised and answered technically). For plain fact lookups the agent does
what the baseline does, adds an LLM call, and brings no gain. The price is about twice
the latency and 63% more tokens, which matters on a laptop CPU but is modest compared
with the cost of an unsupported statement in patent work.

**RQ2 (verification).** Verification makes every statement's support visible, and
regenerating poorly grounded answers raised grounding by 4 points without losing key
facts (6.2). It does not fix misattribution (a true statement citing the wrong passage),
and it adds 7–9 s per stage. Its value is mainly transparency: the user sees which
sentences to double-check.

**RQ3 (retrieval design).** Three design choices behave differently. Claim-aware chunking
barely changes retrieval metrics but is decisive for answer grounding (65% vs. 48%),
because a verifiable citation needs a passage that says one thing. More passages help up
to about six (key facts +12 points) and then mostly add cost. A cross-encoder reranker is
the strongest single retrieval improvement (MRR 0.26 → 0.52), at 15 s per answer.

**Agent design (F, H).** Choosing tools per question gives cleaner evidence at lower cost
than running every tool, and a rule-based planner was at least as accurate as an LLM
planner while saving one LLM call. Where the question structure is predictable (claim
numbers, patent numbers, comparison wording), explicit rules are more reliable than
asking the LLM to classify.

**RQ5 (live data).** For patents published after the model's training data, live
retrieval is not an improvement but a precondition: the LLM alone answered every such
question confidently and wrongly (73% of its statements unsupported, never "I don't
know"), while the agent with live EPO access found the right patent and claim every time
(6.5). The experiment also exposed a failure mode the other experiments could not: when
the asked patent is unavailable, a retrieval system can silently answer from a different
document. Statement-level verification does not catch this, because each statement does
match the passage it cites; the check has to be on *which document* the question is
about. This was fixed, and is a reason to test RAG systems on questions whose answer is
deliberately absent.

**RQ4 (verifier accuracy)** is answered only partially (6.6). Against one AI-assisted
annotator, no verifier agrees well beyond chance (κ ≤ 0.24). The deployed NLI verifier is
deliberately strict: it finds more of the unsupported statements than the LLM judge, at
the price of flagging about a third of supported ones. For a tool whose purpose is to
show users what to double-check, false alarms are the cheaper error, but they mean the
grounding scores in this report understate how much of each answer is actually supported.
With only 9 unsupported statements in the sample, the comparison between methods is
indicative at best.

## 7.2 Verification as a component
Statement-level verification makes grounding measurable and visible to the user (each
unsupported sentence is highlighted), but the verifier is itself a model with errors.
Development showed two systematic weaknesses of a small NLI model: sensitivity to premise
length (fixed by sentence windows) and statements that combine two sources ("both
systems…"), which are judged against each source separately. Reporting the verifier's
agreement with human judgement (Experiment I) shows how far grounding scores can be
read as accuracy: in this project, as a conservative lower bound rather than an exact
measure.

## 7.3 Limitations
- **Dataset size.** 53 test questions over 16 patents in three domains, one run each; small
  differences are not detectable, and results may not transfer to other technical fields
  or languages.
- **One LLM.** All reported runs use Qwen3-8B; larger or hosted models may change both the
  absolute numbers and the size of the agent's advantage.
- **Labels not human-verified.** Questions, relevance labels and key facts were written by
  an AI assistant and audited by the same assistant, not checked by people. An
  independent test set and content-based labels limit, but do not remove, the risk of
  systematic labelling errors. Retrieval metrics and key-fact recall depend on them.
- **Verifier validated only weakly.** Experiment I used 150 statements labelled by a single
  team member with AI assistance (no second annotator, so no inter-annotator agreement),
  with only 9 unsupported statements; grounding scores remain the NLI verifier's
  judgement, which is stricter than the labels.
- **Planner in the main experiments.** Experiments A, F and G used the LLM planner (the
  `auto` default); Experiment H suggests the rules planner would do at least as well.
- **Key-fact recall** is exact matching and misses paraphrases (e.g. "the temperature at
  arrival" vs. the key fact "estimated temperature at arrival"), so it is conservative.
- **False premises.** A question that presupposes something absent from the patent ("which
  neural network does the Kalman-filter patent train?") was answered about what the patent
  does contain instead of rejecting the premise; verification flagged most of that answer.
- **Single live source.** EPO OPS only; USPTO and Lens clients are designed but not
  implemented. EPO supplies English claims for EP and some WO publications only, so the
  live question set has no US or CN patents, and its 30 questions ask only about claims.
- **Deployment scope.** Accounts with private data per user, but no email verification,
  password reset by email or multi-factor login (docs/security.md).

## 7.4 Threats to validity
- *Internal:* tuning on the dev questions is separated from reporting on test questions;
  run-order effects on latency are controlled by interleaving and counterbalancing.
- *Construct:* grounding depends on the verifier (low agreement with one AI-assisted
  annotator, κ 0.16; strict);
  passage-level retrieval metrics depend on label completeness (document-level metrics
  reported too); key-fact recall is exact substring matching.
- *External:* three domains, English-language US patents and applications.

## 7.5 Ethical and legal considerations
The system describes technical content and similarity and states that it does not assess
novelty, validity or infringement; legal-opinion questions are answered with a disclaimer
and a technical comparison only. Documents can stay on the user's machine when local
models are used.
