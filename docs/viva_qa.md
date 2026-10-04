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
Both exist (Experiment H). The LLM planner is more flexible but costs an extra call and
made mistakes we had to guard against: it called a valid question "out of scope" and
sent plain lookups to similar-patent search. We now accept its output only when the
question supports it.

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
Experiment I: humans label statements, and we measure the verifier's agreement with them
(accuracy and Cohen's κ). Two humans also label the same statements; their agreement is
the ceiling.

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
Small dataset and three domains; one LLM; a verifier that can still make mistakes
(especially on statements combining two sources); EPO is the only live source; no user
accounts.

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
