# Viva questions and answers

Short answers in plain language, with where to look for detail. Practise saying them
aloud; examiners usually ask "why", not "what".

## The idea

**1. What does your project do, in one sentence?**
It answers questions about patents using only retrieved patent text, cites every
sentence, and automatically checks each sentence against its source to detect
hallucinations.

**2. Why not just use ChatGPT?**
A plain LLM answers from memory and can invent details without any source. In patents, a
wrong number or a feature attributed to the wrong patent changes the meaning. We make
the model answer from evidence and verify it.

**3. What is RAG?**
Retrieval-Augmented Generation: first retrieve relevant passages, then let the LLM write
an answer from them. It's like an open-book exam instead of a closed-book one.

**4. What makes it "agentic"?**
An agent decides the steps for each question: a claim question fetches that claim
directly, a comparison collects evidence from each patent separately, a "find similar"
question searches patent databases. A fixed RAG pipeline does the same thing every time.
(docs/diagrams/3_answer_flow)

**5. What is a hallucination, and how do you detect it?**
A statement not supported by the source. We split the answer into statements and use an
NLI model to check whether the cited passage entails each one: supported, partially
supported, or unsupported. (docs/diagrams/4_verification)

## Design choices

**6. Why one chunk per claim?**
Claims are the unit patent people care about. It lets the answer cite "claim 3" exactly
and lets the agent fetch a claim directly without similarity search.

**7. Why hybrid search?**
Embeddings find passages with the same *meaning*; keyword search finds exact terms such as
part names and numbers, which matter in patents. We merge both lists with Reciprocal Rank
Fusion: each passage scores Σ 1/(60 + rank).

**8. What is an embedding?**
A list of numbers (1,024 here, from BGE-M3) representing a text's meaning; similar texts
have nearby vectors. We compare them with cosine similarity.

**9. What is pgvector and HNSW?**
pgvector adds vector columns and similarity search to PostgreSQL. HNSW is a graph index
that finds nearest vectors quickly without comparing against every passage.

**10. Why PostgreSQL and not a separate vector database?**
One system stores documents, vectors, full-text indexes, the API cache and every run
record, with transactions across them. Fewer moving parts for a project of this size.

**11. Why LangGraph?**
It makes the agent an explicit graph of steps with conditions. That's easier to test,
explain and evaluate than a free-form loop where the LLM decides everything.

**12. Rules planner or LLM planner?**
Both exist, and Experiment H compared them on the test set: the rules planner got all 53
intents right, the LLM planner 49 (92.5%), with the same tools and answer quality, and the
LLM planner costs one extra LLM call. During development it also made mistakes we had to
guard against (calling a valid question "out of scope", sending plain lookups to
similar-patent search), so we accept its output only when the question supports it.

**13. Why a local model (Qwen3-8B)?**
Zero cost, documents never leave the machine, and results are reproducible. The code
works with any OpenAI-compatible API by changing `.env`.

**14. What is NLI?**
Natural Language Inference: given a premise and a hypothesis, decide entailment,
contradiction or neutral. Premise = evidence passage; hypothesis = answer sentence.

**15. Why check sentence windows instead of the whole passage?**
We found the small NLI model loses entailment when the passage has extra sentences: the
same statement scored 0.99 against its sentence but 0.04–0.38 against the whole
paragraph. So we score each sentence and neighbouring pair and take the maximum (as in
SummaC).

**16. What is a misattributed statement?**
A true statement that cites the wrong passage, e.g. a feature of patent B cited to
patent A. Our second verification pass checks all other passages to detect this.

**17. What happens when grounding is low?**
Below 0.8, the agent retrieves extra passages for each unsupported statement, tells the
model which statements failed, and asks for a rewrite, once. It keeps whichever attempt
is better grounded.

**18. What if the documents don't contain the answer?**
A sufficiency check stops before calling the LLM if nothing relevant was found, and the
LLM is instructed to reply "insufficient evidence" rather than guess.

**19. Legal questions?**
We never give legal opinions. "Does A infringe B?" is answered with a disclaimer and a
technical comparison only.

## Evaluation

**20. How do you know it works?**
A labelled question set, an experiment runner that answers every question with each
system variant, and metrics with 95% confidence intervals. (docs/report/06)

**21. What are precision@k, recall@k and MRR?**
Precision@k: share of the top k passages that are relevant. Recall@k: share of relevant
passages found in the top k. MRR: 1 ÷ the rank of the first relevant passage.

**22. What is the grounding score?**
(supported + ½ × partially supported) ÷ statements checked.

**23. Why confidence intervals?**
With ~50 questions, an average could easily differ by several points by chance. The
bootstrap resamples the questions 2,000 times to estimate that range. We only claim a
difference when the interval of the paired difference excludes zero.

**24. What is a paired comparison?**
Both systems answer the same questions, so we compare question by question
(agent − baseline), which removes the variation between questions.

**25. How do you know the verifier is right?**
We measured it in Experiment I, with limits. One team member labelled 150 answer
statements (with an AI assistant's help) as supported, partly supported or unsupported.
Our NLI verifier caught 5 of the 9 unsupported statements, more than the LLM judge (2 of
9), but it also flagged 30% of the statements the labeller called supported, so it is
strict: our grounding scores are conservative. Agreement beyond chance was low for all
methods (κ 0.16–0.24). Limits: one annotator, AI-assisted, and only 9 unsupported
statements, so this is indicative. The planned fix is a second independent labeller
(the tooling, `make eval-agreement`, is ready). After users saw correct sentences flagged, we
added two modes. Strict (a guarded word-overlap second look) cut false alarms from 41 to
26 of 137 and caught 8 of 9 problems; balanced (Qwen re-checks only the flagged sentences)
cut false alarms to 7 of 137 but caught 5 of 9. Balanced is the default, strict is a
profile setting. These numbers are partly optimistic: some fixes were designed after
looking at all labels.

**26. What is Cohen's κ?**
Agreement corrected for chance. 1 = perfect, 0 = no better than chance.

**27. Why are relevance labels based on content and not chunk IDs?**
Chunk IDs change when you re-chunk. Labels like "the passage containing 'samples every
thermistor'" or "claim 3" work for any chunking, so Experiment B is fair. (We first had a
bug where claim labels couldn't match fixed-size chunks; content anchors fixed it.)

**28. Didn't you tune the system on your test questions?**
No. Questions used during development (dev set) are separate from the test questions,
written independently and frozen before the reported runs.

**29. How did you make latency comparisons fair?**
Variants run interleaved question by question, with the starting variant rotated
(the LLM server caches the previous prompt), after a warm-up, on an idle machine.

**30. What did you find?**
[Fill in after the final runs, from docs/report/07_results.md.]

## Implementation and security

**31. How are API keys protected?**
They live only in `.env` (git-ignored), are loaded as secret types that never print, are
masked in logs, and are used only on the server; the browser talks only to the Next.js
server, which proxies the API.

**32. How do you validate uploads?**
The content must match the extension (PDF magic bytes, DOCX internal structure); size is
limited while the file streams in; DOCX zip bombs are rejected; files are stored under
their hash, not the user's filename.

**33. What prevents abuse or runaway cost?**
Rate limits (20 questions per minute), input length limits, request-size limits, and a
production start-up check that refuses unsafe settings.

**34. What is prompt injection, and are you safe from it?**
Text in a document that tries to give the LLM instructions. Evidence is marked as
untrusted data, the model has no tools that change data, and every sentence is verified.
A crafted document can still influence answers about itself; we state this as a
limitation.

**35. How was it tested?**
Over 300 automated backend tests (with fake models and a separate test database),
frontend unit tests and type checks, browser checks of every page, and real runs with the
local models.

## Limitations and future work

**36. What are the main limitations?**
Labels written and audited by an AI, not verified by people; the verifier checked only
against one AI-assisted annotator (Experiment I: strict, κ 0.16); 53 test questions in three domains, one
run each; one LLM; the main experiments used the LLM planner although the rules planner
did at least as well; EPO is the only live source; false premises are not rejected.

**37. What would you do next?**
More sources (Lens, USPTO), larger multilingual datasets, a stronger verifier that can
combine evidence across sources, claim-element-level comparison, multi-user deployment.

**38. What was the hardest part?**
Measuring honestly. Several bugs only showed up because we evaluated carefully: the NLI
premise-length problem, the chunking-label bias, timing order effects, and the LLM
planner's mistakes on real patents.

## Invention analysis

**39. What does Invention Analysis do?**
You describe an invention; it splits it into technical features, finds the closest
documents (local and live patents), and shows feature by feature where each one is
disclosed, citing the passage, plus a downloadable report.

**40. How is the chart made, and can it hallucinate?**
For each feature and each document, we retrieve that document's best passages and the NLI
verifier decides disclosed / partially / not found. The LLM never fills cells, so the chart
cannot contain an invented disclosure. The LLM only lists features, and those are rejected
unless at least half their words come from the user's description.

**41. Can it say my invention is novel?**
No. It says which features were *not found in the retrieved documents*. Other documents
may disclose them, and novelty is a legal judgement; every result carries that disclaimer.

**42. How did you evaluate it without labels?**
A self-check: each patent's own claim 1 is the "invention". With the patent searchable it
should be found first with all features disclosed; with it hidden, the closest documents
should come from the same domain. It scales to any number of patents with no labelling.
Being easier than real use, it complements the labelled test set.

**43. Why does a claim give better features than a free description?**
A claim already separates the elements with semicolons, so we split it with rules; no LLM
is involved, and every feature is exactly what the drafter wrote.

## Accounts, chat and memory

**44. How are passwords stored?**
Never in plain text: as a scrypt hash with a random salt per user. Checking a login hashes
the attempt and compares in constant time. scrypt is deliberately slow and memory-hungry,
so stolen hashes are expensive to crack.

**45. Why a separate database for users?**
Credentials are the most sensitive data. Keeping them in their own database separates
them from the patent data layer, its queries and its backups; a flaw in search cannot
return a password hash.

**46. How do you stop one user seeing another's documents?**
A middleware identifies the user for each request and sets an owner scope; the search
function every feature uses only returns public patents and that user's documents.
Direct lookups by id return "not found" for other users' items. Tests check this through
listing, search, questions, conversations and comparisons.

**47. How does the chat remember earlier messages?**
Each follow-up is rewritten into a standalone question using the last few turns, e.g.
"and claim 2?" becomes "What does claim 2 of US9178361B2 add?". The rewritten question is
shown, and it goes through normal retrieval and verification, so memory never becomes a
source of unverified facts.

**48. What happens when you upload a document in a chat?**
It is processed like any upload (sections, claims, embeddings), owned by you, and attached
to that conversation; questions in the chat are then answered from the attached documents.

## Results (added after the final runs)

**49. What are your main results?**
On 53 frozen test questions over 16 real patents, compared with a plain RAG pipeline the
agent found the right passage more often (recall@5 39.4% → 51.1%), its answers were
better grounded (66.4% → 72.6%) with fewer unsupported statements (22.2% → 17.2%), all
with 95% intervals excluding zero, at about twice the latency (15 s → 29 s). The biggest
gains were on comparisons and legal-opinion questions; plain lookups gained nothing.
Regeneration added 4 points of grounding; fixed-size chunks dropped grounding from 65% to
48%; the reranker doubled MRR (0.26 → 0.52) at +15 s. On 30 questions about patents
published in 2026 (after the model's training), the LLM alone never said "I don't know"
and 73% of its statements were unsupported, while the agent with live EPO access found
the asked claim every time. Every number is in docs/report/07_results.md with its result
folder.

**50. Who wrote the test questions and labels? Are they reliable?**
An AI coding assistant wrote them from the patent texts, before any system run, and froze
them. After the runs the same assistant audited every item against the patents (4 key
facts corrected, no question changed), and all runs were re-scored. No human verified
them, which we state as a limitation. Two things limit the damage: labels are
content-based (checked automatically against the patent text), and only retrieval and
key-fact metrics depend on them; grounding, latency, tokens and tool choice do not.

**51. Why did the main experiments use the LLM planner if the rules planner was better?**
The `auto` setting picks the LLM planner when a real LLM is configured, and we only
learned that the rules planner was as good from Experiment H, on the test set. Switching
afterwards and re-reporting would be tuning on the test set, so we report what was
measured and list re-running with the rules planner as future work.

**52. Why do you need live data at all? Couldn't the LLM just know the patent?**
Experiment E tested exactly that on 15 patents published in 2026. Asked about them
without retrieval, Qwen3-8B answered all 30 questions confidently, never said it did not
know, and described the wrong invention (a wireless-charging patent became "a
photovoltaic system"). With live EPO access, the agent fetched every named patent and
retrieved the asked claim every time. For new patents, live retrieval is not an
improvement, it is the only way to be right.

**53. How did you get ground truth for the live experiment without labelling?**
The questions ask what a specific claim says, so the answer is the claim text itself,
which we fetched from EPO when building the question set and froze. Answers are scored by
how much of the claim's content they contain and by our verifier against the real claim
text. No one wrote labels, so there is no labelling bias, but the questions are only
about claims.

**54. Did the experiments find any bug in your own system?**
Yes. Without a patent database, asking about a patent that is not in the library made the
agent fall back to searching every document, and it answered with another patent's
claim, naming the asked patent. The verifier missed it, because each sentence matched its
cited passage. We fixed it (the agent now says the patent is not available), added a
regression test, and re-ran that part: 30 of 30 questions correctly declined. We report
the result before and after the fix.

**55. A user saw correct sentences marked as hallucinations. What did you do?**
We traced one answer sentence by sentence. Three causes: the model cited once at the end
of a paragraph (we counted uncited but supported sentences as only partly supported), the
title passage did not say it was a title, and the small NLI model missed paraphrases. We
fixed the first two by rule and added a guarded word-overlap check for the third, chosen
on half of our labels and measured on the other half. The same answer went from 1 of 6 to
5 of 6 verified; the remaining flag is a genuine paraphrase that word matching cannot see.

**56. What happens if the patent I ask about is not in my library?**
The agent searches the European Patent Office: if the library has nothing relevant, or
the model finds the library's passages insufficient, it rewrites the question into patent
terms, searches EP and WO publications first (they come with claims), ranks the hits
against the whole question, imports the best three and answers from them. A "Patent DBs"
switch in the chat does this for every question.

**57. Why not just use the LLM to check everything?**
It is slower (about 4 s per statement on a laptop) and it is lenient: on its own it found
only 2 of 9 unsupported statements, because it accepts plausible reasons and implications.
NLI is fast and strict but misses paraphrases ("likelihood" for "probability"). So NLI
checks everything, and only the sentences it cannot confirm go to the LLM, with a prompt
that accepts synonyms but not added reasons. That keeps cost proportional to doubt.

**58. Can the checker catch an answer that talks about the wrong patent?**
Yes, since this fix: if a sentence names a patent number and its supporting passage comes
from a different patent, it is marked unsupported, however well the words match. Meaning-
based checks alone cannot see this, because the text itself is correct.

**59. Can it answer general questions, like ChatGPT?**
Yes, but differently: it searches the web (Tavily, or Wikipedia without a key) and answers
from the pages it found, citing each sentence and checking it with the same hallucination
checker. ChatGPT answers from what the model remembers; ours answers from sources it can
show you, which is the point of the project. Web pages are used for that answer only,
not stored.

**60. Why not just let the model answer general questions from its own knowledge?**
Because nothing could check it. Experiment E showed the model confidently invents details
about things it has not seen (it called a wireless-charging patent "a photovoltaic
system"). With web pages as evidence, each sentence has a source the checker can compare
against.

**61. What is the Hallucination X-ray?**
A view of the checker's work on one answer. Each sentence is coloured by its verdict, and
clicking it shows the exact passage it was compared with and why it passed or failed. If
the first draft failed the check and was rewritten, the draft is shown beside the final
answer, so you can see which invented sentence was caught and removed.

**62. The X-ray highlights matching words. Is that how the checker decides?**
No. The highlights are only a reading aid that shows which words the sentence and the
passage share. The checker is an NLI model (plus an LLM second opinion for flagged
sentences) that judges whether the passage *means* the sentence is true. A sentence can
share many words with a passage and still be unsupported, for example by changing a number
or reversing a relation.

**63. Did adding the X-ray change your experiment results?**
No. It only displays verdicts the system already computed. The one backend change keeps
the first draft's per-sentence verdicts, which were computed before but only summarised;
answering and checking are unchanged.

**64. What does "Plant a false fact" do?**
It answers your question again, but secretly changes one sentence of the first draft into a
false one (a wrong number, a reversed direction, or an invented detail) while keeping its
citation. The checker is not told which sentence. You then see whether it caught the
planted sentence, and the rewritten answer without it, or an honest "missed" message.

**65. Isn't that cheating, since you know where the error is?**
The checker doesn't know: it checks every sentence exactly as it does normally. Only the
display knows which sentence was planted, so it can show whether it was caught. A miss is
shown as a miss.

**66. Did the test ever fail?**
Yes, and that was useful. The first test changed "40 °C" to "120 degrees" and the checker
missed it: "120" appeared in the patent as a part number (the cooling channels are "120"),
and the LLM second opinion confirmed the sentence while quoting 40 °C in its own reason.
We added a rule that numbers must match with their units and that the LLM cannot confirm
a sentence whose numbers are not in the source. Re-measured on the 150 labelled sentences,
it costs one extra false alarm; five checker tests afterwards were all caught.

**67. How can I see that the system is really "agentic"?**
Open "Agent steps" under an answer, or watch while it works: it shows how the agent read
the question, which tools it chose and in what order, why each was chosen, what each one
found, and how long it took, including any retry or rewrite. A plain RAG pipeline would
always do the same two steps; here the steps change with the question.

**68. Are the "Why" lines the model explaining itself?**
No. They are written by the program from the planner's decision (for example "no document
was named, so the whole library is searched first"), so they always match what actually
happened and cannot be made up by the language model.

**69. How is the landscape map made?**
Each patent's title and abstract is turned into the same 1,024-number meaning vector used
for search (BGE-M3). Similar patents have similar vectors. K-means groups the vectors into
clusters; t-SNE then squeezes the 1,024 dimensions into two so they can be drawn, keeping
neighbours together. The invention is placed the same way, and the five patents with the
most similar vectors are linked to it.

**70. Two dots are close on the map. Are those patents similar?**
Probably, in meaning: nearby dots usually describe similar technology. But flattening
1,024 dimensions into two distorts distances, so the map is for a first overview. The
similarity numbers in the side panel are computed in the full space and are the reliable
ones. Neither says anything about legal overlap.

**71. The answer now appears word by word. Is it a different answer from before?**
No. The model's reply is streamed to the page as it is written instead of being sent when
it is finished. With the same settings (temperature 0) the streamed text is identical to
the text a normal request returns; we checked this against the local model. The
experiments and the /ask API still use the normal request.

**72. If text is shown before it is checked, can the user read a hallucination?**
For a few seconds, yes, and the page says so: the draft is labelled as being written, then
"checking each sentence". Each sentence then takes its verdict colour. Unsupported
sentences are listed struck through while the answer is rewritten, and the answer that
stays in the conversation is the checked one. Showing the draft makes the checking
visible; it does not skip it.

**73. How did the chat get faster without changing the results?**
Mostly by showing it sooner: the first words appear as soon as the model writes them (about
6–11 s instead of waiting about 50 s for everything). Questions about the assistant itself
are answered without a search, and a source that cannot be reached is given up after 5 s
instead of 31. The library, web and patent searches also run at the same time, but we
measured that honestly with an A/B test: it saves only 0–2.5 s, because they share one
embedding model that runs one job at a time. The answers are unchanged.

**74. Why does the page poll the server instead of using WebSockets or streaming the
HTTP response?**
The answer keeps running on the server even if the page changes address, is reloaded or
the connection drops (it happens behind the Next.js proxy and when shared through a
tunnel). A poll twice a second always gets the current state from the server, so nothing
is lost; the page smooths the text between polls so it still reads like typing.

**75. Where do the "Ask next" questions come from? Could they be wrong?**
The language model suggests them after reading the question and the checked answer. They
are questions, not facts: when one is clicked, it goes through the normal search, answer
and check like any typed question. Questions about legal matters (infringement, validity)
are filtered out.

**76. The checker approved a sentence that reversed "increase" to "decrease". What did
you do?**
The NLI model had flagged it; the LLM second opinion then confirmed it, although its own
reason said the passages state "increase". As with changed numbers, the LLM may no longer
overrule the first check when the sentence uses a direction word (increase, higher, above,
before, open, heat, …) whose opposite is in the passages and the word itself is not, or
whose phrase is reversed: a later test wrote "immersion heating systems" where the source
says "immersion cooling", and "heat" did occur elsewhere in it ("heat dissipation"). We
re-measured the checker on the 150 labelled statements before keeping the rule. A first
version added one false alarm ("one or more coils" against "less than"), so it now compares
the word's phrase, not just whether the opposite appears somewhere; with that, no result
changed. One honest limit: our checker test reverses words from a similar list, so those
tests now mostly show this rule working, not the NLI model.

**77. Your system refuses to answer without sources. Why does it now answer "Who won the
2018 World Cup?" from the model's own knowledge?**
Because a chat assistant that says "I couldn't find this" to everyday questions is not
useful, and the user asked for it. But it is kept separate: such answers only appear in the
chat, only when no source had the answer, and they carry a visible label "General knowledge ·
not from sources, not checked". The research answers, the /ask API and all experiments are
unchanged. In our own test one such answer contained a false claim, which shows why the
label is needed.

**78. How does it answer "What day is it?" or "What is 15% of 240?" exactly?**
Those are not questions for a language model. The date comes from the clock in the user's
time zone (sent by the browser) and sums from a small calculator that only accepts numbers
and arithmetic operators, so nothing else can run. Both are decided by simple rules and
answered in under a second.

**79. What happens when the user presses Stop?**
The page tells the server, and the agent stops at its next step; if the model is writing, the
stream is closed mid-sentence, which also stops the model. What was written so far is saved
as a "stopped" message and marked as not checked.

**80. Why offer a cloud model if the project is about running locally?**
Speed: on a laptop, an 8B model needs 10–16 s to write an answer and more to check it; a
hosted model is several times faster. It is optional, chosen per user, off by default, and
the profile page says that questions and passages are then sent to the provider. The
experiments and the report's results all use the local model.

**81. What is the difference between red and violet in the X-ray?**
Red means the sentence contradicts its passage: the passage gives a different number with
the same unit ("50 Hz" where it says "10 Hz") or the opposite direction ("decreases" where it
says "increases"). Violet means no passage says it at all. Both are "unsupported" and count
the same in the grounding score; the split only helps the reader. Red is decided by those
concrete checks, not by the NLI model's contradiction score, which is unreliable on
paraphrases.

**82. How does it know which words are wrong?**
After the verdict, the statement is compared with the passage it was checked against:
numbers with their units, direction words in the same phrase, an added "not", and content
words the passage never uses. These are rules, so they explain a verdict but never change
it; the measured verdicts stay exactly as in Experiment I.

**83. What is a false premise, and what does the system do about it?**
A question that assumes something the sources never say, like "Which neural network does
the Kalman-filter patent train?" when the patent has no neural network. Before writing, the
system finds the question's terms that no retrieved passage uses and tells the writer to say
so plainly if the question assumes them. The answer then starts "The sources do not mention
a neural network" and continues with what they do say. The note is shown only when the
answer itself says this, so a synonym that the word check misses does not raise a false
alarm.

**84. Can the user fix a flagged sentence? Is that not hiding the system's mistakes?**
Yes: "Remove it", or "Rewrite from the source", where the model rewrites only that sentence
from the passage and the checker checks it again; if the sources do not back the rewrite it
is refused. It hides nothing: the original answer and its verdicts are kept, every edit is
listed as "Edited by you", the original can be restored, and the stored claim
verifications still record what the system itself produced.

**85. What is the Fact Checker page for?**
To check any text, for example an answer from another AI assistant, against your own
documents and patents. Each sentence is matched to its closest passages with the same
hybrid retrieval and checked by the same verifier, with the same X-ray. It turns the
project's hallucination detection into a tool for text the system did not write.

**86. Did these changes affect your evaluation results?**
No. The verifier code was not changed; the new information is computed after the verdict.
The false-premise instruction changes what the writer is asked, so it is switched off in
experiment reruns, like the other features added after the experiments.
