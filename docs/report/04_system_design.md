# 3. System Design

## 3.1 Overview
The system has four layers (Figure 3.1): a web frontend, an API backend containing the
ingestion pipeline, the agent and the verifier, a PostgreSQL database with the pgvector
extension, and model services. All models run locally by default (no paid API is
required); live patent data comes from the EPO Open Patent Services.

*Figure 3.1: System architecture (docs/diagrams/1_architecture).*

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS | One asking page (a chat that opens on a search-style start screen), Library, Invention analysis, Patent watch, research pages; proxies `/api` to the backend so no secret reaches the browser |
| API | FastAPI (Python 3.12) | 47 operations; validation, rate and size limits, uniform JSON errors with request IDs |
| Agent | LangGraph | State machine that analyses the question, plans and runs tools, generates, verifies, regenerates |
| Storage | PostgreSQL 17 + pgvector 0.8 | Documents, patents, passages with 1024-d embeddings (HNSW index) and full-text vectors (GIN index), run records for evaluation |
| Models | Qwen3-8B (Ollama), BGE-M3, DeBERTa-v3 NLI, BGE reranker v2-m3 | Generation, embeddings, verification (NLI, with an LLM second opinion), optional reranking |
| External | EPO OPS v3.2; Tavily or Wikipedia | Patent search, bibliographic data, claims and descriptions; web search for general questions |

## 3.2 Ingestion design
Patents are split along their structure rather than at fixed lengths (Figure 3.2): text is
extracted, cleaned (running headers, hyphenation, ligatures), segmented into the standard
sections, and chunked so that **each claim is one passage** and description paragraphs
are grouped up to 400 tokens with 60 tokens of overlap. Every passage keeps its section,
claim number, page and exact character offsets, so citations can point to "claim 3" or
"page 4". Fixed-size chunking is kept as an alternative for Experiment B.

*Figure 3.2: Ingestion pipeline (docs/diagrams/2_ingestion).*

## 3.3 Retrieval design
Each question is searched in two ways: dense similarity of BGE-M3 embeddings (cosine,
HNSW) and PostgreSQL full-text search. The two candidate lists (30 each) are merged with
Reciprocal Rank Fusion, score(d) = Σ 1/(60 + rank), and the top 6 passages (within a
3,000-token budget) are given to the LLM. A sufficiency gate answers "insufficient
evidence" without calling the LLM when no passage is similar enough (cosine < 0.35) and
no keyword matches, which prevents answers from nothing.

## 3.4 Agent design
The agent is an explicit graph (Figure 3.3; generated from code in docs/agent_graph.md):

1. **Analyse:** recognise small talk ("hello", "thanks"), which gets a short reply with
   no retrieval; otherwise classify intent (document question, patent lookup, find
   similar, compare) and extract publication numbers, claim numbers, sections and legal wording,
   using rules or an LLM planner whose output is validated (numbers, sections and the
   similar-search intent are only accepted if the question contains them).
2. **Resolve targets:** map "my battery patent" or "EP1234567" to indexed documents, or
   mark them for fetching.
3. **Plan and execute tools:** `search_uploaded_documents`, `retrieve_evidence`,
   `retrieve_document_section`, `search_patents`, `get_patent_details`,
   `compare_patents`, `extract_key_concepts`, `search_web`, `search_patent_abstracts`.
4. **Check and recover:** if evidence is insufficient, one recovery step broadens the
   search; if the library has no answer (or the model reads its passages and replies
   "insufficient evidence"), the web and patent offices are searched once (Section 3.4.1).
5. **Generate:** a grounded prompt with numbered evidence `[E1]…`; evidence is marked as
   untrusted data (prompt-injection hardening); interpretation is separated from facts;
   legal questions are reframed as technical comparisons with a disclaimer.
6. **Verify and regenerate** (Section 3.5).

*Figure 3.3: Question-answering flow (docs/diagrams/3_answer_flow).*

### 3.4.1 Sources used for one answer (added after the experiments)
To behave like a general assistant without giving up verification, questions that are not
about the user's own documents also draw on outside sources, used for that answer only:

| Question | Sources searched |
|---|---|
| About attached or named documents | Those documents only |
| General ("How do solid-state batteries work?") | Library + web |
| About patents, or with the "Patent DBs" switch | Library + web + patent-office abstracts |
| Topic search ("latest patents on X") | Patent-office abstracts |
| A named patent; "similar to my invention" | Patent imported (full text needed) |

Web pages (Tavily, or Wikipedia when no key is configured) and patent-office hits (title
and abstract) become *transient passages*: ranked by embedding similarity to the
question, dropped below a similarity of 0.55, cited and verified exactly like library
passages, recorded in the run, but never stored in the library or indexed. A question the
LLM planner judges off-topic may use the web but not the patent offices. Web and EPO
requests retry once after a dropped connection, and an answer says when its sources
could not be reached rather than that nothing exists. All of this is switched off in the
experiments (Chapter 6 measured the system without it).

## 3.5 Verification design
Answers are split into statements (disclaimers and the interpretation paragraph are
skipped). Each statement is judged in two passes (Figure 3.4): against the passages it
cites (individually and together), and, if not supported, against all other retrieved
passages. A statement supported only by an uncited passage is *misattributed*. The
grounding score is (supported + ½·partially supported) / statements. If grounding is
below 0.8, the agent retrieves extra passages for each unsupported statement and asks the
model to rewrite with explicit feedback, at most once, and keeps the better-grounded
attempt.

The NLI judgement (Figure 3.5) scores the passage, each of its sentences and each pair of
neighbouring sentences, prefixed with the passage's location and document title, and
takes the maximum entailment probability (≥ 0.5 supported, ≥ 0.15 partial).

**After the experiments**, users saw correct sentences flagged (Section 6.6), and the
application now verifies in up to three stages:

1. **NLI**, as above.
2. **Guarded word-overlap rescue** of what NLI rejects: a statement counts as supported if at
   least 75% of its key words appear in one passage, all its numbers appear there, and it
   adds no negation or opposite direction word ("increases" vs. "decreases").
3. **LLM second opinion** ("balanced", the default): only statements still flagged are
   re-checked by Qwen3-8B (batches of four, three most relevant passages each), which
   accepts synonyms but not added reasons or implications. "Strict" mode, a per-user
   setting, stops after stage 2.

Two rules apply in every mode. A statement that names a patent number cannot be supported
by a passage from a different patent. An uncited statement that a passage supports counts
as supported (citation coverage is reported separately). Chapter 6 reports the original
NLI verifier; Section 6.6 measures the new stages.

*Figure 3.4: Verification (docs/diagrams/4_verification). Figure 3.5: One NLI judgement
(docs/diagrams/4b_nli_judgement).*

## 3.6 Invention analysis
Beyond question answering, the system supports a complete prior-art style workflow. Given
an invention description (or an uploaded draft, whose abstract and claim 1 are used), it
(1) splits the invention into technical features, taking claim elements directly when a
claim is present ("comprising: a; b; and c") and otherwise accepting LLM-listed features
only if at least half of their content words occur in the description; (2) optionally
searches the patent databases with the features' key terms and imports the top results;
(3) ranks candidate documents by Reciprocal Rank Fusion of per-feature retrieval rankings,
excluding the invention's own document; and (4) builds a feature × document chart in which
each cell is decided by retrieving that document's three best passages for the feature and
judging them with the NLI verifier (disclosed / partially disclosed / not found), citing the
passage. The chart is therefore computed rather than generated, and cannot contain an
invented disclosure. Features found in no retrieved document are listed, with an explicit
statement that this is not a novelty assessment.

*Figure 3.7: Invention analysis (docs/diagrams/7_invention_analysis).*

## 3.7 Data model
Thirteen tables (Figure 3.6) separate the corpus (documents, patents, chunks, API cache)
from the record of every answer (queries, agent runs, tool calls, retrieval results, claim
verifications, evaluations) and from the user-facing features (conversations, patent
watches and their hits). Each run stores a snapshot of all settings used, so every
reported number can be traced to its configuration. User accounts and login sessions live
in a **separate database** (`patent_rag_auth`, own migrations); rows in the main database
refer to their owner only by id, so a fault in the patent data layer cannot expose
credentials.

*Figure 3.6: Database schema (docs/diagrams/6_database).*

## 3.8 Design decisions
| Decision | Alternative | Reason |
|---|---|---|
| One passage per claim | Fixed windows | Claims are the legal and technical unit; citations can name the claim |
| Hybrid retrieval with RRF | Dense only | Patent text has exact terms (part names, numbers) that keyword search finds reliably |
| Explicit agent graph | Free-form ReAct loop | Inspectable, testable, and tool selection can be evaluated against labels |
| Local models | Hosted APIs | Zero cost, documents never leave the machine, reproducible |
| PostgreSQL for vectors, text, cache and runs | Separate vector DB + Redis | One service to operate; transactions across corpus and run records |
| Feature chart decided by retrieval + NLI | LLM writes the chart | A generated chart could assert disclosures that are not in the document; a computed one cites a passage for every ✓ |
| NLI verifier | LLM-as-judge only | Deterministic, free, fast; the LLM judge is kept as an alternative (Experiment I) |
| LLM only as a second opinion on flagged statements | LLM judges everything | Cost proportional to doubt; the LLM alone accepted plausible but unstated reasons (Section 6.6) |
| Web pages and abstracts used for one answer | Import everything found | Fast, no library clutter, and still cited and verified; full import only when full text is needed |
| Web answers from cited pages | Model's own knowledge | Only sources can be verified; Experiment E showed the model inventing details about unseen patents |
