---
name: python-ai-applications
description: Build production Python AI applications — LLM clients, RAG pipelines, agents, and FastAPI services — with typed boundaries, validated outputs, and tunable rather than hardcoded defaults. Use when writing or reviewing Python AI/ML code.
---

# Python AI Applications

This skill is the index and the reasoning. The binding specifics live in four rules that activate on file path:

| Rule | Covers |
|---|---|
| `backend/python-structure` | Typing, logging, config, exceptions, async |
| `backend/fastapi-structure` | Routers, dependency injection, error mapping |
| `ai/ai-applications` | Client wrappers, prompts, retrieval, agents |
| `ai/accuracy-validation` | Output parsing, grounding, evaluation |

Numeric and model defaults: `.agents/config/defaults.md`. Deeper material: `reference.md` in this folder.

## Stack posture

Async FastAPI, Pydantic v2 at every I/O boundary, pydantic-settings for configuration, bounded retries on external calls, and a wrapped client per provider. Model identifiers are configuration, never literals.

## Layout

```
src/<project>/
├── api/
│   ├── routers/        # request → service → response, nothing else
│   ├── deps.py         # dependency providers
│   └── main.py         # app, routers, handlers, lifespan
├── core/               # clients: llm, embeddings, vector store
├── services/           # business logic, one concern per module
├── prompts/            # prompt builders, versioned
├── models/             # pydantic request/response/domain models
└── config.py           # Settings
```

The boundary that matters: routers never reach past services, and services never reach past clients. A model call in a router is the single most common structural failure in this stack.

## Defaults are hypotheses

Chunk size, overlap, top-k, embedding model, temperature, and iteration limits are starting points with dates on them, not architecture. The rule is not "use 512" — it is:

1. Start from `defaults.md`.
2. Build the evaluation before tuning: questions with answers in the corpus, questions without, adversarial inputs.
3. Measure precision@k and faithfulness.
4. Change one variable, re-measure, keep what wins.
5. Record the result in the project's decision log so nobody re-tunes it blind.

A tuning change shipped without a measurement is not an improvement; it is a different guess.

## Failure modes to design for

- Retrieval returns nothing → explicit no-context response, never an empty context passed to the model
- Model returns unparseable output → log raw, bounded repair retry, then fail loudly
- Model returns confident nonsense → grounding prompt plus source-carrying responses
- Retrieved document contains an instruction → treated as data, never as instruction
- Agent loops → bounded iterations, raise on the limit
- Provider degrades → timeout, bounded retry, meaningful upstream status code
