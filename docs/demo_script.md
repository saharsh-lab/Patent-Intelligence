# Demo script (about 10 minutes)

Every question below was run on 2026-10-04 with Qwen3-8B + BGE-M3 + NLI on the four
patents listed, and behaved as described. Times are from a MacBook; allow for variation.

## Before the demo (do this 30 minutes ahead)

1. `ollama serve` is running and `ollama list` shows `qwen3:8b`.
2. `.env` uses the real models (keep a copy of the fake-model `.env` as a fallback):
   ```
   LLM_PROVIDER=openai_compatible
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_API_KEY=ollama
   LLM_MODEL=qwen3:8b
   LLM_REASONING_EFFORT=none
   EMBEDDING_PROVIDER=local
   VERIFIER_METHOD=nli
   ```
3. Start the app: `make db-up`, `make run` (API), `make web` (UI) and open
   http://localhost:3000. The sidebar should show **Connected**.
4. **Documents page:** these four patents should be listed as Ready. If not, upload them
   from `experiments/datasets/real_v1/corpus/`. Delete any test files (e.g.
   `wireless_patent.txt`) so only real patents are searched.
   - US9178361B2: detection coils for foreign objects (wireless charging)
   - US10804750B2: Q-factor detection method
   - US20190074730A1: machine-learning foreign object detection
   - US8852772B2: dielectric-fluid battery cooling
5. **Warm up:** ask one question on Ask AI and wait for the answer. The first answer
   loads the models and is slow; later ones are faster.
6. Optional: open Settings and check that the models shown are the real ones.

**Fallback** if Ollama fails during the demo: set `LLM_PROVIDER=fake` in `.env` and
restart the API. Answers become simple quotes from the evidence, but retrieval,
citations, verification and every page still work.

## The story (talk track)

**0:00 Problem (1 min).** "LLMs answer patent questions fluently but invent facts. In
patents one wrong detail changes the meaning. Our system answers only from patent text,
cites every sentence and checks every sentence."

**1:00 Documents (1 min).** Open one patent. Show the detected sections and that each
claim is its own passage. "This is why we can cite 'claim 17' precisely."

**2:00 Ask AI: a normal question (2 min).** Ask:
> How does the machine-learning charging pad decide whether a foreign object is present?

(~35 s) Point out: the citations [E1]… (click one to jump to the evidence), the agent's
steps, the grounding score (~90%), and the verification panel. In our run the verifier
caught one *misattributed* sentence: true, but it cited the wrong passage. "Plain
chatbots can't tell you that."

**4:00 Claim question (1 min).** Select US9178361B2 in the search scope and ask:
> What does claim 17 add?

(~7 s) "The agent recognised a claim question and fetched claim 17 directly, with no
similarity search. The answer is one fully grounded sentence."

**5:00 Comparison (2 min).** Comparison page (or Ask AI with both selected): US10804750B2
and US20190074730A1:
> Compare how these two patents detect foreign objects.

(~35 s) Show the table: every cell cites its own patent; ✓/~/✗ marks from verification.
In our run one statement was flagged unsupported: "This is hallucination detection
happening live."

**7:00 Safety behaviour (1.5 min).**
> What is the retail price of the machine-learning wireless charging pad?

(~13 s) "Insufficient evidence: it refuses to guess."

Then select US10804750B2 and US9178361B2:
> Does the Q-factor patent infringe the detection-coil patent?

(~45 s) "It does not give a legal opinion. It states that, and gives a technical
comparison instead."

**8:00 Invention Analysis (2 min, the highlight).** Invention Analysis page → "Use an
example" (a battery pack with per-cell sensors and a coolant pump) → Analyse (~1–2 min).
Show the features, the closest documents, and click ✓ cells to see the exact passage.
Point at "not found in retrieved documents" and the disclaimer. Download the report.
"This chart is computed by retrieval and verification, not written by the AI, so it
can't invent a disclosure." *(Rehearse this step after the final experiments; time
it on your laptop.)*

**9:30 Evaluation (1 min).** Evaluation page: pick a result. "Every claim we make is
measured: retrieval, grounding, tool choice, cost, with 95% confidence intervals, against
a conventional RAG baseline." Mention one engineering finding (e.g. the NLI premise-length
bug found by evaluation).

**10:30 Close.** Architecture slide (docs/diagrams/1_architecture.png).

## If something goes wrong
| Symptom | Fix |
|---|---|
| Sidebar shows "Disconnected" | the API is not running: `make run` |
| API won't start: "address already in use" | another program uses port 8000: stop it, or run the API on another port and set `BACKEND_URL=http://localhost:<port>` in `frontend/.env.local` |
| Answer takes > 2 minutes | Ollama is loading or busy: wait, or use the fallback |
| "Too many requests" | the rate limit (20 questions/min); wait a minute |
| Different wording than rehearsed | normal: the LLM's wording varies slightly; the behaviour (citations, verification, refusals) is what to show |
