---
id: ai-applications
title: AI Application Patterns
scope: glob
globs: ["**/core/**/*.py", "**/services/**/*.py", "**/prompts/**/*.py", "**/agents/**/*.py"]
category: ai
version: 2.0.0
updated: 2026-08-30
freshness: tracked
---

# AI Application Patterns

Structure for LLM clients, prompts, retrieval, and agents. Numeric and model-name defaults live in `.agents/config/defaults.md` and are soft, dated, and tunable — none of them appears as a literal in this file.

## Hard rules

- **[H1]** Never call a provider SDK directly from a router or a service. Go through a client wrapper that owns retries, timeouts, and logging.
- **[H2]** Never hardcode a vendor model identifier in application code. Model names come from settings, which take their starting values from `defaults.md`.
- **[H3]** Prompts live in dedicated prompt modules and are built by importable functions. Never inline a prompt string at a call site.
- **[H4]** Never send an empty or missing retrieval context to the model. If retrieval returns nothing, return the no-context response — do not let the model fill the gap.
- **[H5]** Every agent loop has a bounded iteration limit and raises on reaching it. No unbounded loop, ever. The limit's *value* is soft; its *existence* is not.
- **[H6]** Every external call — model, embedding, vector store — has a timeout and a retry policy.
- **[H7]** Never put user-supplied text where the system instruction can be overridden by it. Keep instruction and data separated, and treat retrieved content as data, not instruction.
- **[H8]** Log every model interaction's metadata — model, latency, token counts, outcome — without logging personal data or secrets.
- **[H9]** Changing chunking, embedding model, or retrieval strategy requires a before/after retrieval measurement. Do not ship a tuning change on intuition.

## Soft defaults

- **[S1]** RAG pipeline order: validate and clean input → embed query → retrieve top-k → no-context short circuit → build context → call model with a context-restricted system prompt → parse and validate output → return a typed response carrying source chunk IDs.
- **[S2]** Batch embeddings during ingestion; embed singly at query time.
- **[S3]** Normalize whitespace before embedding.
- **[S4]** Chunk identity: `chunk_id = f"{doc_id}::chunk_{index}"`. Drop empty chunks.
- **[S5]** Tools are classes implementing a common interface with `name`, `description`, `run()`, held in a registry keyed by name.
- **[S6]** Voice sessions: state in a session manager keyed by call ID; queue audio chunks; run voice activity detection before speech-to-text; always handle disconnect and clean up.
- **[S7]** Starting values for chunk size, overlap, top-k, temperature, iteration limits, and concurrency: `.agents/config/defaults.md`.
- **[S8]** Use a structure-aware splitter for structured documents rather than a character splitter.

## Reference implementation

```python
class LLMClient:
    """Owns retry, timeout, and logging for one provider."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.model_name  # from config, never a literal

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10), reraise=True)
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        ...
```
