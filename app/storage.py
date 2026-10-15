"""Where uploads and workbooks live, as paths the database can carry.

The API, the CPU workers and the GPU worker may run in different containers
or on the host, each with its own mount point for the same folders. So the
database stores paths relative to settings.upload_dir / settings.output_dir,
and every process resolves them against its own settings.
"""
from __future__ import annotations

import os

from .config import settings


def _rel(base: str, path: str) -> str:
    return os.path.relpath(os.path.abspath(path), base).replace(os.sep, "/")


def _resolve(base: str, stored: str | None) -> str | None:
    if not stored:
        return None
    if os.path.isabs(stored):      # rows written before relative paths
        return stored
    return os.path.join(base, *stored.split("/"))


def upload_rel(path: str) -> str:
    return _rel(settings.upload_dir, path)


def upload_path(stored: str | None) -> str | None:
    return _resolve(settings.upload_dir, stored)


def output_rel(path: str) -> str:
    return _rel(settings.output_dir, path)


def output_path(stored: str | None) -> str | None:
    return _resolve(settings.output_dir, stored)


def remove_quietly(path: str | None) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
