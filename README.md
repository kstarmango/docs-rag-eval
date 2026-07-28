# CITE — a grounded, evaluated RAG assistant

**CITE** answers questions from a documentation corpus with **grounded citations**,
explicit **"I don't know" handling** (no hallucinated answers), and a
**retrieval evaluation harness** that measures answer quality with real numbers.

> Portfolio project demonstrating end-to-end AI application engineering:
> document ingestion → chunking → embeddings → vector search → grounded
> generation → evaluation → deployment.

## Why this exists

Most "chat with your docs" demos stop at "it replies." The hard parts of RAG are
the **retrieval** and **honesty** layers — this project focuses there:

- Every answer cites the exact source doc/section it came from.
- When the docs don't contain the answer, it says so instead of guessing.
- A held-out Q&A eval set measures retrieval hit-rate and no-answer accuracy.
- Retrieved chunks are inspectable (you can see *why* it answered).

The current corpus is the **public [Medusa](https://medusajs.com) merchant
user-guide** (an open-source e-commerce platform) — i.e. the kind of store-admin
help docs a shop runs a customer-support desk over: orders, returns, exchanges,
products, inventory, promotions, shipping. The pipeline is domain-agnostic:
swapping the corpus is a matter of pointing the ingester at a different set of
Markdown docs.

## Stack

| Layer | Choice |
|-------|--------|
| Ingestion | Python — header-based chunking of Markdown/MDX docs (path → citation URL) |
| Embeddings | `fastembed` · `BAAI/bge-small-en-v1.5` (384-dim, local, no API key) |
| Vector store | pgvector (Postgres) · HNSW cosine index |
| LLM | Groq · `llama-3.3-70b-versatile` (OpenAI-compatible API) |
| Backend | FastAPI *(in progress)* |
| Frontend | React — chat UI + source/trace panel *(in progress)* |
| Eval | Python harness — retrieval hit@k + no-answer accuracy *(in progress)* |
| Deploy | Docker → Fly.io / Render *(planned)* |

## Pipeline

```
docs (.md) → [1] ingest → [2] chunk → [3] embed → [4] pgvector
                                                       │
question ──────────────────────► [5] semantic search ─┘
                                        │
                                 [6] grounded answer + citations
                                     (or "I don't know")
```

The basic loop ([1]–[6]) works end-to-end locally. The differentiation layer
(numbers, retrieval traces, UI, deploy) is what the rest of the roadmap builds.

## Status

🚧 In progress — see `PLAN.md` for scope and the current step.
Basic RAG loop (ingest → answer with citations + no-answer handling) is done;
eval harness, inspectable traces, UI, and deployment are next.

## Data source note

Uses the **public** Medusa documentation (MIT-licensed) for a portfolio demo
only. Content is not redistributed commercially.
