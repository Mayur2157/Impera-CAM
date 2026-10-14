---
id: accuracy-validation
title: Accuracy and Output Validation
scope: glob
globs: ["**/core/**/*.py", "**/services/**/*.py", "**/prompts/**/*.py", "**/agents/**/*.py", "**/api/**/*.py"]
category: ai
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Accuracy and Output Validation

Never trust raw model output. Parse, validate, verify.

## Hard rules

- **[H1]** Validate every input before it reaches a model or an embedding call: non-empty, within a length bound, expected type. Reject at the boundary.
- **[H2]** Parse structured output into a schema. Never index into a raw dict from a model response.
- **[H3]** On parse failure, log the raw output before raising, and repair-retry a bounded number of times (`defaults.md`). Do not loop indefinitely.
- **[H4]** A retrieval-grounded system prompt must instruct the model to answer only from the provided context and to say it does not know otherwise.
- **[H5]** When retrieval returns nothing, return the explicit no-context response with empty sources and low confidence. Never call the model with an empty context.
- **[H6]** Factual responses carry their sources. A grounded answer without source identifiers is not shippable.
- **[H7]** Treat every model output that will be executed, rendered, or persisted as untrusted input: no `eval`, no unsanitized HTML, no unparameterized SQL built from model output.
- **[H8]** An AI pipeline change is not done until it has been evaluated — see the checklist below.

## Soft defaults

- **[S1]** Strip markdown fences before JSON parsing.
- **[S2]** Attach a confidence field to factual responses; log a warning on low confidence and consider routing to human review.
- **[S3]** Sanity-check output length; a suspiciously short answer triggers a retry or the fallback.
- **[S4]** Record the prompt version alongside the response for traceability.

## Evaluation checklist

Run for any change to prompts, chunking, retrieval, or model selection:

- [ ] Questions with a clear answer in the corpus → correct and grounded
- [ ] Questions with no answer in the corpus → returns "I don't know", does not invent
- [ ] Adversarial inputs, including prompt-injection attempts inside retrieved documents
- [ ] Retrieval precision@k measured before and after
- [ ] Answer faithfulness to retrieved context measured
- [ ] Latency and cost per request compared to the previous configuration

## Reference implementation

```python
async def parse_structured_output(raw: str, schema: type[T]) -> T:
    clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        return schema.model_validate(json.loads(clean))
    except (json.JSONDecodeError, PydanticValidationError):
        logger.error("Unparseable model output: %r", raw[:2000])
        raise OutputParseError("Model returned unparseable output")
```

```python
if not retrieved_chunks:
    return QueryResponse(
        answer="I don't have relevant information for this question.",
        sources=[],
        confidence="low",
    )
```
