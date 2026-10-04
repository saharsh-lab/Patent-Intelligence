# 8. Conclusion and Future Work

## 8.1 Conclusion
This project built and evaluated an agentic retrieval-augmented system for patent
intelligence that answers questions only from retrieved patent text, cites every
statement, and verifies each statement against its evidence. Patent-aware chunking,
hybrid retrieval, a tool-selecting agent with live patent access, and a two-pass NLI
verifier with regeneration were combined in a working application with a web interface.
[After results: 2–3 sentences summarising the measured effect of the agent and of
verification, with confidence intervals, and the verifier's agreement with humans.]
Equally important for practice, the evaluation framework itself (content-based labels,
paired bootstrap comparisons, controlled timing) exposed several measurement pitfalls
that would otherwise have produced misleading conclusions.

## 8.2 Future work
- Additional patent sources (Lens.org for WO/PCT coverage, USPTO) behind the existing
  source interface, and Experiment E on multi-source retrieval.
- Larger and multilingual datasets; evaluation on prior-art search tasks.
- A stronger or domain-adapted verifier, and verification that can combine evidence from
  several sources for comparative statements.
- Claim-element-level comparison (mapping each element of a claim to evidence in another
  patent), presented strictly as technical similarity.
- Shared team workspaces on top of the existing per-user accounts; email verification.
- A premise check before answering: detect when a question presupposes something the
  evidence does not mention, and say so.
