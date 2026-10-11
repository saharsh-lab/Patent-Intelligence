# Appendix A. Extensions After the Evaluation

The features in this appendix were added after the experiments in Chapters 5 and 6. They change
what the user sees, not how answers are retrieved, generated or checked, so the reported
results still describe the system.

## A.1 Hallucination X-ray

The verifier (Section 3.5) produces a verdict for every sentence of an answer, but a
single "9 of 10 statements verified" line hides that work. The X-ray view exposes it.
Each checked sentence is coloured: green when its cited passage supports it, amber when it
is only partly supported or a passage it did not cite supports it, and red when no passage
supports it. Selecting a sentence opens an inspector with the passage it was judged
against, the checker's reason and score, and the words the passage shares with the
sentence. The shared words are a reading aid only; the verdict comes from the entailment
model and, for flagged sentences, the LLM second opinion.

When the first answer fails the check and is regenerated with feedback (Section 3.5), the
X-ray shows the rejected draft beside the final answer, with the dropped sentences struck
through and the grounding of both. To support this, each attempt now stores its
sentence-level verdicts alongside its counts.

While testing the view, a layout defect was found: in conversations taller than the
screen, the top of the thread could not be scrolled into view. It was caused by a
decorative background layer that the flex layout shrank while keeping its negative
margin, and is fixed.

## A.2 Checker test: planting a false sentence

A verifier is easiest to trust when it can be watched catching a mistake. The chat's X-ray
therefore offers "Plant a false fact": the same question is answered again, and before
verification one sentence of the first draft is made false in a way typical of
hallucinations, keeping its citation so it still looks sourced. A number is changed (e.g.
"10 Hz" to "30 Hz"); if the draft has none, a direction word is reversed ("increases" to
"decreases"); otherwise a plausible invented detail is added. The verifier is not told
which sentence was changed. If it flags the sentence, the answer is regenerated with that
feedback even when the overall grounding is above the regeneration threshold, and the
X-ray shows the rejected draft with the planted sentence marked. The outcome is reported as
it happened, including a miss. The mode is off in production and never used by the
experiments.

The first live test found a real weakness. The planted "below 120 degrees Celsius" (the
patent says 40 °C) passed as supported: the lexical rescue found "120" in the passage as the
reference numeral of the cooling channels, and the second-opinion LLM confirmed the sentence
while quoting 40 °C in its own reason. After the number rule described in Section 6.6, five
checker tests on the battery patent (four changed numbers, one invented detail) were all
caught and removed by regeneration, against three of five before. Five tests are an
illustration, not a measurement; the cost of the rule on the labelled statements is one
additional false alarm in 137 (Section 6.6).

## A.3 Live agent trace

The agent's decisions were visible only after the fact, as a list of tool calls. The chat
now shows them while they happen: every graph node (the question-answering flow of Figure 3.3) and every tool call becomes a
row with its status, a one-line result, its duration and, for tools, the reason the
planner chose it. The reasons are generated from the planner's decision rather than asked
of the language model, so they cannot disagree with what the agent did. The page polls the
rows once a second; the finished trace is stored with the answer and can be reopened. In a
browser check with the local models, a 50-second answer showed its first row after 8
seconds and the three chosen tools (library, web, patent abstracts) by 22 seconds. The
agent's behaviour is unchanged.

## A.4 Patent landscape map

To see a technology area at a glance, the patents returned for a topic are placed on a map.
Each title and abstract is embedded with BGE-M3 (the retrieval model, Section 3.3),
k-means with k-means++ starts [26] groups the vectors (k grows with the number of patents, up to six) and t-SNE [25]
projects them to two dimensions (PCA when scikit-learn is not installed). Patents and
documents in the user's library appear as squares, using the mean vector of their
passages; an invention, described or chosen from the library, appears as a star joined to
its five most similar patents. Each cluster is named by the two words or phrases most
typical of it; patent boilerplate ("the utility model discloses") had to be excluded for
the names to be meaningful. Nothing is imported. The page states that 2D distances are
approximate and that the similarity is technical, not legal.
