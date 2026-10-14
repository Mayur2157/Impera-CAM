---
id: python-structure
title: Python Structure
scope: glob
globs: ["**/*.py"]
category: backend
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Python Structure

Typing, logging, configuration, errors, and async for Python code.

## Hard rules

- **[H1]** Public functions carry parameter type hints and a return type.
- **[H2]** Use built-in generics (`list[T]`, `dict[K, V]`) and `T | None`. Not `List`, `Dict`, `Optional`.
- **[H3]** Data crossing an I/O boundary is a Pydantic model, not a bare dict.
- **[H4]** No `print()` for diagnostics. Use a module-level logger.
- **[H5]** Log errors with `exc_info=True`. A logged exception without a traceback is a lost bug.
- **[H6]** Never log secrets, credentials, tokens, full payment data, or personal data beyond what the project's retention rules allow.
- **[H7]** Raise domain exceptions derived from a project base error. Never `raise Exception(...)`.
- **[H8]** Catch specific exceptions. No bare `except:`, and no `except Exception` that swallows without logging and re-raising or converting.
- **[H9]** Read configuration through a settings object (`pydantic-settings` or equivalent). Never `os.environ[...]` scattered through the codebase.
- **[H10]** No mutable default arguments. `items: list | None = None`, then `items = items or []`.
- **[H11]** I/O in an async context is awaited. Never call a blocking client inside a coroutine — use the async client or `asyncio.to_thread`.

## Soft defaults

- **[S1]** Module header: a docstring naming module and purpose, `from __future__ import annotations`, then `logger = logging.getLogger(__name__)`.
- **[S2]** Log levels: `debug` for internals, `info` for milestones, `warning` for a triggered fallback, `error` for a failure.
- **[S3]** Split functions past roughly 50 lines.
- **[S4]** `asyncio.gather` for independent concurrent work; a semaphore to bound concurrency (limit in `defaults.md`).
- **[S5]** CPU-bound work off the event loop via `asyncio.to_thread`.

## Reference implementation

```python
"""
Module: <module_name>
Purpose: <one line>
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base for all domain errors in this project."""


class ValidationError(AppError):
    """Input failed a domain invariant."""
```

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    llm_api_key: str
    # Model identifiers are configuration, never literals in code.
    # See .agents/config/defaults.md.
    model_name: str
```
