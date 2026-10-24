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

## A.5 Live chat

Users found the chat slow: a typical answer took 47–60 seconds and nothing appeared until
all of it was ready. The chat now shows the answer as it happens. Above the answer, the
stage (understand, search, write, check) and the sources appear as the tools find them.
The draft is shown word by word while the model writes it; the reply is streamed, and with
the same settings it is the same text as an ordinary request. While the draft is checked,
a scan passes over it, and each sentence then takes its verdict colour. If sentences fail,
they are shown struck through and the rewritten draft is typed out. The view is fed by the
same twice-a-second poll as the agent trace (A.3); the agent's behaviour does not depend on
it, and experiments do not use it.

Three changes make answers faster without changing them, the first only slightly. The
library, web and patent-abstract searches that the planner selects together run
concurrently, each with its own database connection, and their results are used in plan
order; because they share the embedding model, which runs one job at a time, an A/B test on
three questions saved 0–2.5 seconds of the search stage. Questions about the assistant itself
("Can I talk anything?") are answered immediately with its capabilities and example
questions; the pattern matches none of the 157 experiment questions. A web source that does
not accept a connection within five seconds is abandoned. In a browser test with the local
model, a new question showed its first words after 5.7 seconds and was complete and checked
after 27.8. After each answer, the model suggests three follow-up questions, written once
the answer is shown so that they do not delay it.

The tests also found two accuracy problems. The planner judged "How do solid-state
batteries work?" out of scope, so only the web was searched, and the passages found were
about solid-state drives. When the planner says out of scope and a live search is planned,
a one-word technology check now decides whether patent filings are searched, and Wikipedia
is searched with the planner's key words rather than the question. Checker tests
that reversed a direction ("increase" to "decrease", "immersion cooling" to "immersion
heating") were passed by the LLM second opinion, by the key-word rescue and once by the NLI
model itself. No stage may now accept a statement whose direction word is reversed within its
phrase relative to its supporting passage; the labelled results are unchanged (Section 6.6),
and because the test's planter uses an overlapping word list, such tests now mainly exercise
this rule.

## A.6 Everyday questions and a chat-assistant feel

Further user feedback asked for the chat to behave more like a general chat assistant.
Questions that need no source are now answered exactly: the date and time from the clock,
in the user's time zone, and arithmetic from a calculator that accepts only numbers and
arithmetic operators. Both are recognised by rules and take under a second. When a general
question finds nothing in the library, the patent offices or the web, or for a writing
task such as a poem, the model answers from its general knowledge. Such answers carry the
label "General knowledge · not from sources, not checked", because the checker has no
passages to check them against; in a test one of them contained a false statement, which is
the reason for the label. They appear only in the chat, never in the /ask API or the
experiments.

Chat answers are written in a chat style (a direct answer first, then short paragraphs and
lists) at a length the user chooses, and are rendered with lists, numbered steps and line
breaks. As in common chat assistants, an answer can be stopped (what was written is kept,
marked as not checked), copied with its sources, asked again, or edited and resent, and its
sources appear as numbered chips. The local model is kept loaded between questions, and a
faster hosted model can be chosen per user; it is off by default, and the profile page
states that questions and passages are then sent to the provider.

## A.7 A more informative checker and a Fact Checker page

The X-ray now says what is wrong in a flagged sentence, not only that it is flagged. After
the verdict, the sentence is compared with the passage it was checked against, and the
words at fault are underlined: a number the passage does not have (with the number it does
have), a direction reversed within its phrase, an added negation, or words the passage
never uses. Unsupported sentences are split into two colours: "contradicts its source",
when the passage gives a different number with the same unit or the opposite direction,
and "not found in the sources" otherwise. These explanations are computed by rules after
the verdict and never change it, so the verdicts and grounding scores reported in
Chapter 6 are unaffected.

A question can presuppose something no source says (Section 7.3). Before the answer is
written, the question's terms that no retrieved passage uses are found and the writer is
asked to say plainly when the question assumes them. With the battery document as the
only source, questions about a neural network or LiDAR sensors were answered "The sources do
not mention ..." followed by cited facts, and three ordinary questions raised no such note.
The detection is word-based, so a synonym can trigger it; the note is therefore shown only
when the answer itself states the absence. It is switched off in experiment reruns.

A flagged sentence can be removed, or rewritten from its source: the model rewrites only
that sentence from the passage and the checker checks it again, refusing the rewrite if the
sources do not back it. The original answer and its verdicts are kept and can be restored.
A new Fact Checker page applies the same checking to any pasted text, for example an answer
from another AI assistant: each sentence is matched to its closest passages in the user's
documents and patents with the same hybrid retrieval and checked by the same verifier. It
also lists what the checker found in the user's earlier answers.

