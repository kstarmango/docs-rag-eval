# Decisions

Why this project is built the way it is. Each entry is a decision, the
alternative considered, and the trade-off accepted. These are engineering
judgment calls, not just configuration.

---

## D-001 · Positioning: an *evaluated, honest* assistant, not another "chat with your docs"

- **Context:** "Chat with your docs" RAG demos are a commodity — no-code SaaS
  does them per-seat. Copying that yields an 80%-identical portfolio.
- **Decision:** Compete on the layers those demos skip — retrieval quality
  measured with numbers, honest refusal, error analysis, and an inspectable
  retrieval trace. The corpus is only there to make the demo legible.
- **Trade-off:** Less flashy than a multi-tenant upload-your-PDF product; wins
  on the signals a technical buyer actually reads.

## D-002 · Corpus: Medusa merchant docs (switched from n8n)

- **Context:** Needed a corpus that reads as a realistic support desk.
- **Decision:** Public Medusa **user-guide** (open-source e-commerce admin docs:
  orders, returns, products, promotions). 72 docs → 605 chunks.
- **Why:** Two-angle market check pointed at SMB e-commerce as the most
  reachable buyer for a support assistant. Store-admin how-to is a real,
  bounded support domain.
- **Trade-off:** Domain-specific, but the pipeline is corpus-agnostic (see D-010).

## D-003 · Embeddings: `bge-small-en-v1.5` (384-dim), local via fastembed

- **Context:** No GPU, free tier, ~600 chunks, must run on CPU with no API key.
- **Decision:** `BAAI/bge-small-en-v1.5` through `fastembed` (ONNX, CPU).
- **Why:** Larger embedders add latency and memory for a small accuracy gain;
  the reranker (D-005) recovers most of that gain anyway. Local embeddings mean
  ingestion and retrieval cost nothing and leak nothing.
- **Trade-off:** Slightly weaker first-stage recall, bought back by reranking.

## D-004 · Vector store: pgvector (Postgres), HNSW cosine

- **Context:** Need vector search that is easy to run and reason about.
- **Decision:** Postgres + `pgvector`, HNSW index with cosine distance, in Docker.
- **Why:** One familiar system for data + vectors; SQL makes the corpus filter
  (D-010) and inspection trivial. No extra vector-DB service to operate.
- **Trade-off:** Not the fastest at web scale — irrelevant at this size, and
  Postgres is a credible production choice reviewers respect.

## D-005 · Two-stage retrieval: cross-encoder reranker on top of vector search

- **Context:** Error analysis on the first eval run showed the failures were a
  *ranking* problem, not a *recall* problem — the right doc was retrieved but
  ranked below surface-word-collision matches (a "bulk import" query pulled the
  *Bulk Editor* and *Export* docs above *Import Products*).
- **Decision:** Retrieve top-20 by vector, then re-score with a cross-encoder
  (`ms-marco-MiniLM-L-6-v2`) that reads the query and chunk together; return top-k.
- **Result:** Recall@1 69.2→76.9, Recall@5 94.9→100.0, MRR .816→.861,
  retrieval failures 2→0, over-refusal 5.1→2.6%.
- **Trade-off:** Extra model load + per-query latency; worth it — it eliminated
  both retrieval failures. Toggleable via `RAG_RERANK` for the before/after story.

## D-006 · LLM: Groq `llama-3.3-70b-versatile`, OpenAI-compatible, free tier

- **Context:** Portfolio must cost nothing to run and stay swappable.
- **Decision:** Groq via the OpenAI-compatible API; model behind
  `LLM_MODEL`/`LLM_BASE_URL`/`API_GROQ_KEY` env vars. `llama-3.1-8b-instant`
  (separate token budget) is used for cheap plumbing smoke tests.
- **Why:** Free, fast, and provider-agnostic — pointing at OpenAI/Anthropic is
  one env change.
- **Trade-off:** Free tier is 100k tokens/day per model, so evaluation runs are
  paced; the retrieval metrics are computed with no LLM to stay free.

## D-007 · Honesty is enforced by the LLM, not only a score threshold

- **Context:** A similarity cutoff (`MIN_SCORE`) was supposed to catch
  out-of-scope questions, but bge-small packs unrelated English into cosine
  0.4–0.5, so the cutoff barely fires.
- **Decision:** Treat the LLM's context-only refusal as the real safety net;
  measure it directly (out-of-scope refusal accuracy + over-refusal on real
  questions) instead of trusting the score gate.
- **Why:** Verified behavior beats an assumed threshold. Out-of-scope questions
  are refused even though retrieval still returns *something*.
- **Trade-off:** Depends on prompt discipline; that's exactly why it's measured.

## D-008 · Keep one honest failure (q28) instead of overfitting the gold set

- **Context:** "How do I *add* a new customer" fails — the docs say "*create* a
  customer" (an add/create vocabulary gap). The right doc reaches top-5 but the
  create-customer *chunk* isn't retrieved.
- **Decision:** Let it **refuse rather than answer from the wrong section**, and
  document it as a known limitation. Do not tune the gold set to hide it.
- **Why:** A safe failure (refuse) is the correct behavior, and an honest report
  is worth more than a rounded-up number. Fix (query expansion / chunk-level
  scoring) is a tracked next step.
- **Trade-off:** Recall@1 isn't 100%. That's the honest number.

## D-009 · Order questions handled by tool-calling, not RAG

- **Context:** Real support has two question types: **A** answerable from docs
  ("how do I refund"), and **B** needing live data ("where is my order #1234").
  RAG can only do A.
- **Decision:** Give the LLM tools (`search_help_docs`, `lookup_order`,
  `find_orders_by_email`) and let it route. Orders come from a deterministic
  mock store; when no tool can help (e.g. no order id), it escalates instead of
  inventing details.
- **Why:** B is most of a store's real support volume, and it shows agentic
  routing + a hard line against hallucinating account data.
- **Trade-off:** Orders are mocked, not a real backend — the routing and safety
  behavior is the point, and the tool is a drop-in for a real API.

## D-010 · Multi-corpus infrastructure, but a second corpus deferred

- **Context:** "Does it work on *my* data?" is a completeness gap. But arbitrary
  PDF upload would turn this into the commodity chatbot D-001 rejects — and a
  gold set can't exist for arbitrary user docs, killing the eval story.
- **Decision:** Build the pipeline corpus-aware (a `corpus` column, per-corpus
  ingest/replace, a scoped search filter, a UI knowledge-base selector), but
  ship one corpus. A second corpus is added only with its own gold set.
- **Why:** Gets the generalization signal without regressing to "upload and
  hope." The infra is done; adding a corpus is a data step, not a rebuild.
- **Trade-off:** The selector shows one option today ("more coming soon").

## D-011 · Demo frontend is dependency-free HTML/JS

- **Context:** The demo exists to make retrieval *inspectable*, not to show off a
  frontend framework.
- **Decision:** A single static `index.html` (vanilla JS) served by FastAPI —
  conversation thread, retrieval trace with vector vs. reranker scores, KB
  selector. No build step, no framework.
- **Why:** Zero build/deploy friction and nothing to rot; the trace UI is the
  actual differentiator, and it needs no framework.
- **Trade-off:** Not a showcase of React/state management — a deliberate scope
  choice, stated so it doesn't read as inability.

## D-012 · Multi-turn passes trimmed text history, not full tool plumbing

- **Context:** Follow-ups ("when will it arrive?") need prior context, but
  replaying every tool call bloats the prompt.
- **Decision:** Carry only user/assistant *text* turns (last 8) back into the
  prompt; the model re-derives or re-calls tools as needed.
- **Why:** Enough context for pronoun/reference resolution across turns
  (verified: "it" resolved to the prior order), at a fraction of the tokens.
- **Trade-off:** Very long conversations lose the oldest turns — acceptable for
  a support assistant.
