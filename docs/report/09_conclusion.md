# 8. Conclusion and Future Work

## 8.1 Conclusion
This project built and evaluated an agentic retrieval-augmented system for patent
intelligence that answers questions only from retrieved patent text, cites every
statement, and verifies each statement against its evidence. Patent-aware chunking,
hybrid retrieval, a tool-selecting agent with live patent access, and a two-pass NLI
verifier with regeneration were combined in a working application with a web interface.
On a frozen test set of 53 questions over 16 real patents, the agent improved passage
retrieval (recall@5 39.4% → 51.1%) and the grounding score of its answers (66.4% →
72.6%) over a conventional RAG pipeline, with the largest gains for claim, comparison and
legal-opinion questions, at about twice the latency; regeneration added 4 points of
grounding, and claim-aware chunking proved essential for verifiable answers. On 30 questions about patents published in 2026, live EPO
retrieval was decisive: the LLM alone answered every one confidently and mostly wrongly,
while the agent found the asked patent and claim every time; the same experiment exposed
and led to the fix of a misattribution bug when a patent is unavailable. Against
one AI-assisted annotator, the NLI verifier proved strict (it flags about a third of
supported statements) and agreed only slightly beyond chance (κ 0.16), so grounding
scores are best read as conservative. These results rest on AI-written test labels that
were not verified by humans.
Equally important for practice, the evaluation framework itself (content-based labels,
paired bootstrap comparisons, controlled timing) exposed several measurement pitfalls
that would otherwise have produced misleading conclusions.

## 8.2 Future work
- Additional patent sources (Lens.org for WO/PCT coverage, USPTO) behind the existing
  source interface, and live questions beyond claims (description, comparisons).
- Larger and multilingual datasets; evaluation on prior-art search tasks.
- A stronger or domain-adapted verifier, and verification that can combine evidence from
  several sources for comparative statements.
- Claim-element-level comparison (mapping each element of a claim to evidence in another
  patent), presented strictly as technical similarity.
- Human verification of the test labels, and a second independent annotator for
  Experiment I (inter-annotator agreement, `make eval-agreement`), with a larger sample
  containing more unsupported statements.
- Calibrating the NLI verifier's thresholds on such labels to reduce false alarms.
- Repeating the main experiments with the rules planner, and with more than one run per
  question.
- Shared team workspaces on top of the existing per-user accounts; email verification.
- A premise check before answering: detect when a question presupposes something the
  evidence does not mention, and say so.
