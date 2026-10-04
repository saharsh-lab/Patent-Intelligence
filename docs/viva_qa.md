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
