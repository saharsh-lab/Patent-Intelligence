# Key Concepts (viva preparation)

Plain-language explanations of every important idea in this project, in the order
they appear in the pipeline.

---

**Large Language Model (LLM).** A neural network trained on huge amounts of text to
predict the next word. It can write fluent answers, but it only "knows" what it saw
during training and can confidently state things that are false.

**Hallucination.** When an LLM produces a statement that sounds correct but is not
supported by any source, e.g. inventing a claim number or a filing date. Dangerous in
the patent domain, where every detail matters.

**Retrieval-Augmented Generation (RAG).** Instead of asking the LLM to answer from
memory, we first *retrieve* relevant passages from trusted sources and give them to
the LLM with the instruction "answer using only this evidence, and cite it". Like an
open-book exam instead of a closed-book one.

**Chunking.** Patents are long; LLMs have a limited input size and retrieval works
best on focused passages. So documents are split into chunks of a few hundred words.
We split along patent sections (claims, abstract…) so each chunk stays meaningful and
carries its page number and section for citation.

**Embedding.** A model converts a piece of text into a list of numbers (a *vector*,
here 1024 numbers) that represents its meaning. Texts with similar meaning get
vectors that point in similar directions, even if they use different words
("wireless charging" ≈ "inductive power transfer"). We use **BGE-M3**, a free,
multilingual embedding model that runs locally.

**Cosine similarity / distance.** Measures the angle between two vectors.
Similarity 1 = same direction (same meaning), 0 = unrelated.
Distance = 1 − similarity. pgvector's operator for cosine distance is `<=>`.

**Vector database.** A database that can efficiently answer "which stored vectors are
closest to this one?". We don't need a separate product: **pgvector** adds a `vector`
column type and similarity operators to PostgreSQL, so text, metadata, and vectors
live in one database and can be queried together with ordinary SQL.

**HNSW index.** Comparing a query against every stored vector is slow when there are
millions. HNSW (Hierarchical Navigable Small World) builds a layered graph of
neighbours so the search can hop quickly toward the closest vectors. It is
*approximate*: very fast, and nearly always finds the true nearest neighbours.

**Keyword (full-text) search.** PostgreSQL turns text into a `tsvector`: stemmed
words with stop-words removed ("Sensors are coupled" → `sensor`, `coupl`). A `GIN`
index makes matching fast. Good for exact terms, part numbers, and patent numbers,
which embeddings can blur.

**Hybrid retrieval.** Run vector and keyword search, then merge the two ranked lists.
We use **Reciprocal Rank Fusion (RRF)**: each passage scores Σ 1/(60 + rank) across
the lists, so passages ranked well by both methods rise to the top.

**Reranking.** Retrieval is fast but rough. A *cross-encoder reranker* (BGE reranker)
reads the question and each candidate passage *together* and outputs a precise
relevance score. It's too slow to run on the whole database, so we use it to reorder
only the top ~30 candidates.

**Agent.** A program in which an LLM decides *what to do next* instead of following a
fixed script. Here the agent decides whether a question needs the uploaded document,
a live patent search, a comparison, or several of these.

**Tool calling.** The agent is given a list of functions ("tools") with descriptions,
such as `search_patents(query, date_from)`. The LLM replies with *which tool to call
and with what arguments*; our code runs the tool and returns the result. The LLM never
touches the database or APIs directly.

**LangGraph.** A library for writing agents as a *state graph*: nodes are steps
(analyze, plan, retrieve, generate, verify), edges say what runs next, and some edges
are conditional ("if evidence is insufficient, go back to retrieval"). This makes the
agent's control flow explicit, testable, and easy to draw in a report, unlike a
free-running loop.

**Grounding.** An answer is *grounded* when every factual statement in it can be
traced to a specific piece of retrieved evidence.

**Claim-level verification.** After the answer is written, we split it into small
factual statements and check each one against the evidence (using a natural-language
inference model or an LLM judge). Grounding score = supported statements ÷ total.
Unsupported statements are flagged or trigger extra retrieval and regeneration.

**Evaluation metrics.**
- *Precision@k*: of the top k passages retrieved, how many were relevant?
- *Recall@k*: of all relevant passages, how many appeared in the top k?
- *MRR*: how high was the first relevant result? (1/rank, averaged)
- *Faithfulness*: does the answer only say things the evidence supports?
- *Answer relevance*: does the answer actually address the question?
- *Tool-selection accuracy*: did the agent choose the expected tools?

**Database migration.** A versioned script that changes the database structure
(create table, add column). Like git commits for the schema: they can be applied
(`upgrade`) and undone (`downgrade`), so every developer and the test database have
exactly the same structure. We use **Alembic**.

---

## Added in Phase 2 (document ingestion)

**Magic bytes.** The first few bytes of a file identify its real format: PDFs start
with `%PDF-`, DOCX files are ZIP archives starting with `PK`. We check these instead of
trusting the filename, so a renamed executable called `patent.pdf` is rejected.

**SHA-256 hash (deduplication).** A fingerprint computed from the file's bytes. The
same file always gives the same 64-character hash; any change gives a different one.
If an uploaded file's hash already exists, we return the stored document instead of
paying to extract and embed it again.

**Running headers/footers.** Text printed on every page, e.g. "U.S. Patent … Sheet 3
of 9 … US 10,123,456 B2". Left in, it would pollute every chunk and confuse
retrieval, so we drop short blocks that repeat at the top or bottom of most pages.

**Section-aware chunking.** Instead of cutting text every N words, we cut along the
patent's own structure: a chunk never mixes the Abstract with the Claims, and every
claim is its own chunk. Answers can then cite "Claim 3" precisely. Whether this
actually improves retrieval is tested in Experiment B against plain fixed-size chunks.

**Chunk overlap.** Consecutive chunks share a sentence or two, so an idea that falls
on a chunk boundary is still fully contained in at least one chunk.

**Fake (hashing) embeddings.** For tests we don't want to download a 2 GB model or pay
an API. Each word is hashed to a position in the vector, so texts sharing words get
similar vectors. That captures word overlap but not meaning, so it is only for
testing the pipeline, never for experiments.

---

## Added in Phase 3 (basic RAG)

**Reciprocal Rank Fusion (RRF).** How we merge the vector and keyword result lists.
A passage's score is the sum of 1/(60 + its rank) in each list. Because only ranks are
used, we never compare a cosine similarity (0–1) with a keyword score (different
scale). A passage ranked 2nd by both methods beats one ranked 1st by only one method.

**Sufficiency gate.** Before calling the LLM, we check whether anything relevant was
found: at least one keyword match, or a vector similarity above a threshold. If not,
we answer "insufficient evidence" immediately. This saves money and removes the
temptation for the model to answer from its own memory.

**Numbered evidence and citation checking.** Passages are given to the LLM as [E1],
[E2]… and it must cite them. Afterwards we check every label: citing [E9] when only
E1–E6 exist is a *fabricated citation*, a measurable form of hallucination.

**Citation coverage.** The share of answer sentences that cite at least one passage.
High coverage is necessary but not sufficient: a sentence can cite a passage that
doesn't actually say what the sentence claims. Checking that is *claim-level
verification* (Phase 8).

**Supported information vs. interpretation.** The model must put any analysis that goes
beyond the passages in a separate "Interpretation:" paragraph, so the UI can show
clearly which statements come from evidence and which are the model's own reasoning.

**Prompt injection.** Uploaded documents are untrusted text. A document could contain
"ignore previous instructions…". We tell the model that evidence is data, not
instructions, and strip anything in the evidence that imitates our own delimiters or
labels.

**Reasoning ("thinking") models.** Some models, such as Qwen3, write a hidden chain of
reasoning before answering. It costs time and tokens. For grounded answering over
given evidence we turn it off (`reasoning_effort=none`) and never show it to users.

---

## Added in Phase 4 (web UI)

**Frontend / backend split.** The browser runs the Next.js app (React components). It
never talks to the database or the LLM; it calls the FastAPI backend over HTTP. Next.js
forwards `/api/...` requests to the backend ("rewrites"), so secrets and the backend
address stay on the server.

**OpenAPI and generated types.** FastAPI describes every endpoint and response shape in
a machine-readable OpenAPI document (`/openapi.json`). We generate TypeScript types
from it, so if the backend changes a field the frontend fails to compile instead of
breaking silently at runtime.

**Evidence-first answer display.** Citation chips ([E1]) are clickable and scroll to the
exact passage; cited and uncited passages are marked; model interpretation is shown in
a separate, labelled box; and the run summary states what was searched without
exposing hidden model reasoning. This is what makes an answer *checkable* by the user.

---

## Added in Phase 5 (patent sources)

**Publication number and kind code.** A patent document is identified by country +
number + kind code, e.g. `EP1234567A1`. The kind code says what stage the document is:
for the EPO, `A1` is a published application with search report and `B1` is a granted
patent. The same invention can have several documents (A1, then B1).

**Patent family.** Filings for the same invention in different countries (EP, US, WO…)
form a family, identified by a family ID. Useful to avoid showing "the same" invention
five times (Phase 7 deduplication).

**CPC (Cooperative Patent Classification).** A hierarchical code for the technical
field, e.g. `H01M10/486` = batteries → secondary cells → temperature measurement.
Searching by CPC finds relevant patents that use different words.

**CQL.** The query language of EPO OPS, e.g.
`ta all "battery thermal" and cpc=H01M10/48 and pd within "20150101 20241231"`
(`ta` = title+abstract, `pa` = applicant, `pd` = publication date). We build it from the
form fields and show it in the UI, so every search is transparent and reproducible.

**API cache and fair use.** EPO's free tier has hourly and weekly limits. Every search
and detail response is stored in our database for a week, so repeating a search (or
re-running an experiment) costs no quota and returns identical evidence, which matters
for reproducibility.

**Interface / adapter pattern.** All sources implement one interface (`search`,
`get_details`) and return the same `PatentRecord`. The rest of the system doesn't care
which source the data came from, so adding Lens or USPTO later touches one file.

**Mock HTTP testing.** Tests never call the real EPO service: an in-process fake server
(`httpx.MockTransport`) returns saved responses. Tests are therefore fast, free,
repeatable, and can simulate failures like quota errors.

---

## Added in Phase 6 (the agent)

**Intent classification.** The first thing the agent decides is *what kind of task* the
question is: answer from documents, look up a specific patent, find similar patents,
compare, or out of scope. Everything else (which tools, which prompt) follows from it.

**Planner: rules vs. LLM.** Rules (regular expressions) are free, instant and
predictable but miss paraphrases. The LLM understands paraphrases but can return
invalid output, so its JSON is validated and the rules act as a fallback. Patent
numbers proposed by the LLM are discarded unless they literally appear in the question,
so the agent can't fetch a patent the user never mentioned.

**Target resolution.** Turning "my battery patent" or "EP1234567" into a concrete source
in the database. If it's ambiguous (two candidates match equally), the agent asks
instead of guessing, because guessing wrong made it search for the wrong invention.

**State machine / LangGraph.** The agent's steps are nodes; the shared state (question,
targets, evidence, tool log) flows between them; conditional edges are decisions
("enough evidence?"). Unlike an open-ended "LLM decides everything" loop, every
path is known in advance, bounded, testable and can be drawn for the report.

**Recovery.** When a step yields nothing (e.g. a patent search with too many keywords),
the agent tries one fallback strategy (fewer keywords, broader scope) before giving up.
The number of attempts is capped to control cost.

**Agentic vs. baseline (Experiment A).** Baseline: always retrieve top-k from the local
index, then answer. Agentic: choose tools and sources per question. Both store runs
in the same format, so their answer quality, grounding, latency and cost can be
compared on the same questions.

---

## Added in Phase 7 (multi-source intelligence)

**Patent family deduplication.** EP…A1 (application), EP…B1 (grant), US…, WO… can all
describe one invention. We group them (by family ID, or by number without the kind
code) and show one representative, preferring documents with full text (EP/WO) and
granted versions, with the others listed as "also published as".

**Semantic similarity ranking.** To decide which search results are most relevant to
the user's invention, we embed the invention's title + abstract + first claim and each
candidate's title + abstract, and sort by cosine similarity. This measures how close the
*descriptions* are in meaning, not legal similarity, novelty or infringement.

**Structured comparison.** A table of aspects (technical field, problem, components,
operation, main claim) × sources. Evidence is gathered *per source*, so one long patent
can't crowd out the other.

**Cross-source citation.** A cell about patent B that cites a passage from patent A.
The citation label is real, but it supports the wrong patent. We detect and remove
these automatically, and count them as a grounding metric.

**Extractive vs. abstractive.** Extractive = copy the relevant sentence from the passage
(cannot hallucinate, but can be clumsy or pick a poor passage). Abstractive (LLM) =
rewrite and summarise (readable, but can state things the passage doesn't say). We
offer both and fall back to extractive when the LLM's output is unusable.

---

## Added in Phase 8 (claim-level verification)

**Claim.** One checkable statement in the answer, here a sentence (or a table cell).
Disclaimers and the clearly labelled "Interpretation" are not checked.

**NLI (natural language inference).** A model that reads a *premise* (the evidence
passage) and a *hypothesis* (the answer's statement) and outputs probabilities for
*entailment* (the passage says it), *contradiction* (the passage says the opposite)
and *neutral* (the passage doesn't say it). We use a small free model
(DeBERTa-v3-xsmall, ~280 MB, runs locally in ~50 ms per pair). Example: "sampled at
10 Hz" vs. a passage saying "samples every thermistor at 10 Hz" → entailment 0.99.

**Grounding score.** (supported + ½ × partly supported) ÷ statements checked. 1.0
means every statement is backed by the evidence it cites.

**Misattribution.** A statement that is true according to *some* passage, but not the one
it cites. It shows the model mixing up sources, which is common when comparing patents.

**Verify-and-regenerate.** If grounding is below a threshold, the agent fetches extra
evidence for each unsupported statement, tells the model which statements were
unsupported, and asks for a rewrite. The new answer is verified too, and whichever
attempt is better grounded is shown. It's bounded to one retry by default for cost.

**Sentence windows.** Small NLI models are trained on one-sentence premises. Given a whole
paragraph, they often say "not entailed" even when one sentence states the claim exactly.
So each claim is checked against every sentence (and every pair of neighbouring sentences)
of a passage, and the best score counts.

**Verifier errors.** The verifier itself can be wrong: *false alarms* (flagging a correct
paraphrase) and *misses* (passing an unsupported claim). Its accuracy must be measured
against human labels before its numbers are trusted in the paper (Phase 9).

## Added in Phase 9 (evaluation framework)

**Ground truth / labels.** What the correct result is, written by people *before* looking
at system output: which passages answer a question, which facts the answer must contain,
which tools a sensible agent should use. Metrics compare the system with these labels.

**Precision@k and recall@k.** Of the top *k* passages retrieved, what share is relevant
(precision), and what share of all the relevant passages was found (recall)? Example: one
relevant passage, k = 5, found at rank 2 → precision@5 = 0.2, recall@5 = 1.0. With a single
relevant passage, precision@k can never exceed 1/k, so recall and MRR are more informative.

**MRR (mean reciprocal rank).** 1 ÷ the rank of the first relevant passage, averaged over
questions. Found first → 1.0; found third → 0.33; not found → 0.

**Key-fact recall.** The share of labelled facts ("10 Hz") that appear in the answer. A
cheap, repeatable stand-in for "is the answer correct?". It cannot recognise paraphrases.

**Answer vs. abstain.** For unanswerable questions, the correct behaviour is to say the
evidence is insufficient. This metric is right when the system answers answerable
questions *and* abstains on unanswerable ones.

**Tool-selection precision/recall.** Precision: of the tools the agent used, how many were
expected? Recall: of the expected tools, how many did it use?

**Confidence interval (bootstrap).** With 20 questions an average of 80% could easily have
been 70% or 90% with slightly different questions. The bootstrap estimates that range:
resample the questions with replacement 2,000 times, compute the mean each time, and take
the middle 95%. If two systems' intervals overlap a lot, the data doesn't show which is
better.

**Paired comparison.** Both systems answer the *same* questions, so we compare them
question by question (variant − baseline) and bootstrap that difference. A difference is
"clear" only if its 95% interval excludes zero. Otherwise we say "no clear difference on
this dataset", which is not the same as "no difference".

**Cohen's kappa (κ).** Agreement between two raters (a verifier and a human, or two
humans), corrected for the agreement they would reach by chance. 1 = perfect, 0 = chance
level. Raw accuracy can look high just because most statements are "supported".

**Dev/test split.** Tune on the dev questions, report on the test questions, which were
never looked at during tuning. Otherwise the system is fitted to the questions it is
graded on. (Phase 9's smoke run changed two planner rules after seeing dev results:
allowed on dev, not on test.)

**Reproducibility.** Every result folder stores the config, the full settings of every
variant (without secrets), package versions and a SHA-256 fingerprint of the dataset, so
anyone can tell exactly how a number was produced.

## Added in Phase 11 (hardening)

**Rate limiting.** Allow at most N requests per minute, then answer "429 Too Many Requests"
with a `Retry-After` time. Here it caps the number of LLM calls (cost), EPO calls (quota)
and uploads per minute.

**Spoofable headers.** `X-Forwarded-For` normally carries the real client's IP through
proxies, but a client can write anything into it. A rate limiter that trusted it could be
dodged by sending a new fake IP each time, so we trust it only behind a proxy we control.

**Zip bomb.** A tiny compressed file that expands to gigabytes. A .docx is a ZIP archive,
so we check the expanded size before opening one.

**Streaming size limit.** Rejecting an oversized upload *while* it arrives, instead of after
the server has already written the whole file to disk.

**Security headers.** Instructions to the browser: don't guess content types (`nosniff`),
don't let other sites embed this page (`X-Frame-Options`, against clickjacking), don't
cache private answers (`no-store`), and only load code and data from our own origin
(Content-Security-Policy).

**Least privilege.** The containers run as an ordinary user, not root, and the ports are
bound to localhost, so a bug in one component gives an attacker as little as possible.

**Threat model.** Writing down what we protect, from whom, and what is deliberately out of
scope (here: user authentication). Saying what a system does *not* protect against is part
of a good security answer.

## Added after Phase 12 (invention analysis)

**Feature (of an invention).** One technical element: a component, a step or a property.
A patent claim lists them explicitly ("comprising: a sensor; a pump; and a controller"),
so a claim gives the most precise features.

**Feature chart (claim chart).** A table of features × documents saying, for each cell,
whether that document discloses that feature, with the passage as evidence. Patent
professionals build these by hand when looking for prior art; here retrieval plus the
NLI verifier fill each cell.

**Computed, not generated.** The language model only helps split the description into
features (and those must reuse the user's own words). Whether a document discloses a
feature is decided by retrieval and the verifier, with a citation, so the chart cannot
invent a disclosure.

**Self-check evaluation.** An evaluation that needs no human labels because the right
answer is known by construction: a patent's own claim, used as the "invention", should find
that patent first. It scales to thousands of patents; it is easier than real use (same
wording), so it complements, not replaces, the labelled question sets.

**Prior art (careful wording).** Earlier documents describing the same technology. The
system shows *technical overlap with the documents it retrieved*; it never says an
invention is novel, because unretrieved documents may disclose the same thing and novelty
is a legal judgement.

## Added after Phase 12 (accounts, chat and memory)

**Authentication vs. authorisation.** Authentication: proving who you are (email +
password → session). Authorisation: what you may access (only your own documents and
conversations). Both are needed; logging in alone protects nothing if every user can
read every document.

**Password hashing (scrypt).** Passwords are never stored, only a slow, salted hash. To
check a login we hash the attempt the same way and compare. "Slow" is the point: each
guess costs an attacker who stole the database ~16 MB of memory and milliseconds.

**Session cookie.** After login the server stores a random token's hash and gives the
browser the token in a cookie. httpOnly: JavaScript cannot read it (protects against XSS).
SameSite=Lax: other websites' forms cannot send it (protects against CSRF).

**Separate database for accounts.** User credentials live in `patent_rag_auth`, apart from
the patent data. A bug in the search layer cannot expose password hashes, and the two can
be backed up, secured and scaled separately.

**Data isolation (owner scope).** Each request runs "as" its user; the lowest search layer
only ever returns public patents and that user's documents. Because the rule sits where
every search passes, a new feature cannot accidentally leak another user's data.

**Conversation memory by question rewriting.** Instead of pasting the chat history into
the answer prompt (where it could be mistaken for evidence), the follow-up is rewritten
into a standalone question. Memory changes *what is searched for*; the answer is still built
and verified only from retrieved patent text.
