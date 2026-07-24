# Shopify Support Assistant (RAG)

A production-minded RAG (Retrieval-Augmented Generation) assistant that answers
questions from the **public Shopify Help Center**, with **grounded citations**,
**"I don't know" handling** (no hallucinated answers), and a **retrieval
evaluation harness** that measures answer quality with real numbers.

> Portfolio project demonstrating end-to-end AI application engineering:
> document ingestion → chunking → embeddings → vector search → grounded
> generation → evaluation → deployment.

## Why this exists

Most "chat with your docs" demos stop at "it replies." The hard part of RAG is
the **retrieval** and **honesty** layers — this project focuses there:

- Every answer cites the exact source doc/section it came from.
- When the docs don't contain the answer, it says so instead of guessing.
- A held-out Q&A eval set measures retrieval hit-rate and answer quality.
- Retrieved chunks are inspectable in the UI (you can see *why* it answered).

## Stack

| Layer | Choice |
|-------|--------|
| Ingestion | Python (sitemap-driven crawl of help.shopify.com) |
| Embeddings + vector store | pgvector (Postgres) |
| LLM | Claude API |
| Backend | FastAPI |
| Frontend | React (chat UI + source/trace panel) |
| Eval | Python eval harness (retrieval hit@k + answer grading) |
| Deploy | Docker → (Fly.io / Render) |

## Status

🚧 In progress — see `PLAN.md` for scope, weekly plan, and current step.

## Data source note

Uses the **public** Shopify Help Center (`help.shopify.com`) for a portfolio
demo only. Crawling respects `robots.txt` and a 1s crawl delay; content is not
redistributed commercially.
