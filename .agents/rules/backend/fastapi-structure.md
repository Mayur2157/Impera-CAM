---
id: fastapi-structure
title: FastAPI Structure
scope: glob
globs: ["**/api/**/*.py", "**/routers/**/*.py", "**/main.py"]
category: backend
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# FastAPI Structure

Router, dependency, and error-handling shape for FastAPI services.

## Hard rules

- **[H1]** A router does exactly three things: validate the request, call the service layer, return the typed response. No business logic, no model calls, no database queries in a router.
- **[H2]** Every route declares a `response_model`.
- **[H3]** Dependencies are injected, not constructed inside handlers.
- **[H4]** Never leak an internal exception message, stack trace, or SQL to a client. Log the detail; return a safe message.
- **[H5]** Map domain exceptions to meaningful status codes — 422 validation, 404 not found, 409 conflict, 503 upstream unavailable. An unhandled error is 500 with a generic body.
- **[H6]** Expose a health endpoint that does not require authentication and does not disclose internals.
- **[H7]** Validate and bound every input at the boundary: size limits, length limits, allowed types. See `accuracy-validation` [H1].

## Soft defaults

- **[S1]** Layout: `api/routers/*.py`, `api/deps.py`, `services/*.py`, `core/*.py`, `prompts/*.py`, `models/*.py`.
- **[S2]** One-line docstring on every route — it becomes the OpenAPI summary.
- **[S3]** Cache settings construction with `lru_cache`.
- **[S4]** Version the API prefix (`/api/v1`).
- **[S5]** Register a global handler for the project's base error type.
- **[S6]** Use lifespan handlers for startup and shutdown, and log both.

## Reference implementation

```python
router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    service: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    """Answer a question from the indexed corpus."""
    try:
        result = await service.query(request.question)
        return QueryResponse.model_validate(result.model_dump())
    except LLMError as e:
        logger.warning("Upstream model unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e
    except Exception as e:
        logger.error("Unhandled error in /rag/query", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
```

```python
# api/deps.py
@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    return LLMClient(settings)


def get_rag_service(
    llm: LLMClient = Depends(get_llm_client),
    embedder: EmbeddingClient = Depends(get_embedding_client),
    store: VectorStore = Depends(get_vector_store),
) -> RAGService:
    return RAGService(llm=llm, embedder=embedder, store=store)
```
