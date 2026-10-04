# 7. Discussion

> Revise after the final results. The structure and the limitations below stand.

## 7.1 Interpretation
[After results: answer RQ1–RQ4 in a few sentences each, citing tables. Explain *why* the
agent helps or does not, using per-type results (e.g. direct claim retrieval for claim
questions, balanced evidence for comparisons) and the cost in latency and tokens.]

## 7.2 Verification as a component
Statement-level verification makes grounding measurable and visible to the user (each
unsupported sentence is highlighted), but the verifier is itself a model with errors.
Development showed two systematic weaknesses of a small NLI model: sensitivity to premise
length (fixed by sentence windows) and statements that combine two sources ("both
systems…"), which are judged against each source separately. Reporting the verifier's
agreement with humans (Experiment I) is therefore a prerequisite for interpreting any
grounding score.

## 7.3 Limitations
- **Dataset size.** [n] test questions over [N] patents in three domains; small
  differences are not detectable, and results may not transfer to other technical fields
  or languages.
- **One LLM.** All reported runs use Qwen3-8B; larger or hosted models may change both the
  absolute numbers and the size of the agent's advantage.
- **Labels.** Written by the project team; mitigated by two-person checking and an
  independent test set, but relevance judgements remain partly subjective.
- **Key-fact recall** is exact matching and misses paraphrases.
- **Single source implemented.** EPO OPS only; USPTO and Lens clients are designed but not
  implemented; Experiment E [depends on EPO access].
- **Prototype scope.** No user authentication; single-user deployment.

## 7.4 Threats to validity
- *Internal:* tuning on the dev questions is separated from reporting on test questions;
  run-order effects on latency are controlled by interleaving and counterbalancing.
- *Construct:* grounding depends on the verifier (measured in Experiment I); passage-level
  retrieval metrics depend on label completeness (document-level metrics reported too).
- *External:* three domains, English-language US patents and applications.

## 7.5 Ethical and legal considerations
The system describes technical content and similarity and states that it does not assess
novelty, validity or infringement; legal-opinion questions are answered with a disclaimer
and a technical comparison only. Documents can stay on the user's machine when local
models are used.
