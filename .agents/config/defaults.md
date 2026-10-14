---
title: Tunable Defaults
version: 2.0.0
updated: 2026-08-30
---

# Tunable Defaults

**Everything in this file is SOFT.** These are starting points, not architecture. Any value here may be changed for a project with a one-line reason. None of them is a correctness requirement.

Three of these categories go stale on their own — model names, pricing surfaces, and library APIs. Treat a value whose `verified` date is more than 180 days old as unverified: check the provider's current documentation before using it, and update this file with what you find.

## Rule for model and vendor identifiers — [HARD]

**No rule file, skill, or generated code may hardcode a vendor model identifier.** Model names live here, or in the project's settings object, and nowhere else. Before using any model name from this file, confirm it is still offered by the provider. A model identifier is a fact about the world on the day it was written, not a standard.

## Embeddings

| Setting | Default | Verified | Notes |
|---|---|---|---|
| Embedding model (general) | `text-embedding-3-small` | 2026-08-30 | Verify against provider docs before use. Choose on evaluated recall, cost, latency — not on this table. |
| Embedding model (high accuracy) | `text-embedding-3-large` | 2026-08-30 | Only after measuring that the small model underperforms on your corpus. |
| Dimensions | provider default | — | Reduce only if the vector store forces it and you have re-measured recall. |

## Chunking

| Setting | Default | Notes |
|---|---|---|
| `chunk_size` | 512 tokens | Starting point. Correct size depends on document type, tokenizer, and query shape. Tune against measured retrieval quality. |
| `chunk_overlap` | 64 tokens | Roughly 10–15% of chunk size is a reasonable band. |
| Splitter | recursive character, separators `["\n\n", "\n", ".", " "]` | Structured documents (tables, code, legal clauses) usually want a structure-aware splitter instead. |
| Retrieval `top_k` | 5 | Raise until precision@k stops improving, then stop. |

**Required before shipping any change to these values:** a before/after retrieval measurement. Changing chunking without measuring is guessing.

## Agents

| Setting | Default | Notes |
|---|---|---|
| `max_iterations` | 10 | A bounded limit is HARD (see `ai-applications` H5). The number 10 is soft — set it to the task's real ceiling. |
| Tool call timeout | 30s | Per tool, not per run. |
| Concurrency limit for model calls | 5 | Enforce with a semaphore; raise only against observed rate limits. |

## Temperature

Starting points for common task shapes. Measure on your own evals before treating any of these as settled.

| Task | Temperature |
|---|---|
| Structured extraction / JSON output | 0.0 |
| Classification | 0.0 |
| Factual Q&A / RAG | 0.1–0.2 |
| Summarization | 0.3 |
| Conversational agent | 0.5–0.7 |
| Creative generation | 0.7–1.0 |

## Retries

| Setting | Default | Notes |
|---|---|---|
| Attempts | 3 | That retries exist on external calls is HARD. The count is soft. |
| Backoff | exponential, 2s–10s | Add jitter under real concurrency. |
| Structured-output repair retries | 2 | Beyond 2, fail loudly rather than burning tokens. |

## Frontend

| Setting | Default | Notes |
|---|---|---|
| Breakpoints tested | 375 / 768 / 1440 | That responsive behavior is verified is HARD; the exact widths are soft. |
| Accessibility target | WCAG 2.2 AA | HARD as a target. The specific success criteria that apply depend on the surface. |
| Type scale steps | 6 | Soft. |
