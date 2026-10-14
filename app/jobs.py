"""Job store — now backed by MySQL, not an in-process dict.

Architecture
------------
* The web process writes Job + FileTask rows to MySQL, then submits work to a
  thread pool.  Workers read/update those rows directly.
* PDF passwords are NEVER persisted.  They live in _PASSWORDS (memory only)
  for the duration of the worker, then are deleted.
* Scale path: swap the ThreadPoolExecutor for Celery + Redis without changing
  the API surface.
"""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .config import settings
from .db.base import SessionLocal
from .db.models import FileTask, Job, Usage

_POOL = ThreadPoolExecutor(max_workers=settings.workers)

# Passwords held in memory only — keyed by job_id, cleared after the worker runs.
# A lock protects concurrent access from multiple submit threads.
_PW_LOCK = threading.Lock()
_PASSWORDS: dict[str, str | None] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create(
    files: list[tuple[str, str]],
    tenant_id: str,
    user_id: str,
    password: str | None = None,
    use_ocr: bool = True,
    dpi: int = 300,
    bank: str | None = None,
) -> Job:
    """Persist a new job and kick off background processing."""
    db = SessionLocal()
    try:
        job = Job(
            tenant_id=tenant_id,
            user_id=user_id,
            status="queued",
            use_ocr=use_ocr,
            dpi=dpi,
            bank=bank,
        )
        db.add(job)
        db.flush()          # get job.id before tasks

        for name, path in files:
            db.add(FileTask(job_id=job.id, name=name, path=path))

        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    # Store password in memory only — never on disk or in the DB
    with _PW_LOCK:
        _PASSWORDS[job_id] = password

    _POOL.submit(_run, job_id, tenant_id)
    return get(job_id)


def get(job_id: str) -> Job | None:
    db = SessionLocal()
    try:
        return (
            db.query(Job)
            .filter(Job.id == job_id)
            .first()
        )
    finally:
        db.close()


def list_for_tenant(tenant_id: str, limit: int = 50) -> list[Job]:
    db = SessionLocal()
    try:
        return (
            db.query(Job)
            .filter(Job.tenant_id == tenant_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def job_to_dict(job: Job) -> dict:
    """Safe serialisation — password is never included."""
    tasks = []
    for t in job.file_tasks:
        tasks.append({
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "progress": t.progress,
            "message": t.message,
            "result": t.result_data,
            "error": t.error,
        })

    done = sum(1 for t in job.file_tasks if t.status in ("done", "error"))
    total = max(1, len(job.file_tasks))

    return {
        "id": job.id,
        "status": job.status,
        "use_ocr": job.use_ocr,
        "dpi": job.dpi,
        "bank": job.bank,
        "created": job.created_at.isoformat() if job.created_at else None,
        "progress": int(100 * done / total),
        "files": tasks,
    }


def purge(max_age_seconds: int | None = None):
    """Remove finished jobs older than the retention window."""
    cutoff_ts = time.time() - (max_age_seconds or settings.retention_seconds)
    from datetime import datetime, timezone
    cutoff = datetime.utcfromtimestamp(cutoff_ts)

    db = SessionLocal()
    try:
        old = (
            db.query(Job)
            .filter(
                Job.created_at < cutoff,
                Job.status.in_(["done", "error"]),
            )
            .all()
        )
        for job in old:
            # clean up uploaded files
            for task in job.file_tasks:
                try:
                    if os.path.exists(task.path):
                        os.remove(task.path)
                except OSError:
                    pass
            db.delete(job)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _run(job_id: str, tenant_id: str):
    from .core.pipeline import process as run_pipeline

    with _PW_LOCK:
        password = _PASSWORDS.pop(job_id, None)

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            return
        job.status = "running"
        db.commit()

        for task in job.file_tasks:
            # Re-read each task fresh so we have the right db session
            task = db.query(FileTask).filter(FileTask.id == task.id).first()
            task.status = "running"
            task.message = "starting"
            db.commit()

            def _report(pct: int, msg: str, _tid=task.id):
                _db = SessionLocal()
                try:
                    _t = _db.query(FileTask).filter(FileTask.id == _tid).first()
                    if _t:
                        _t.progress = pct
                        _t.message = msg
                        _db.commit()
                finally:
                    _db.close()

            # tenant-scoped output directory keeps files isolated
            tenant_out = os.path.join(settings.output_dir, tenant_id)
            os.makedirs(tenant_out, exist_ok=True)

            try:
                result = run_pipeline(
                    task.path, tenant_out,
                    password=password,
                    use_ocr=job.use_ocr,
                    dpi=job.dpi,
                    progress=_report,
                    source_name=task.name,
                    bank=job.bank,
                    tenant_id=tenant_id,
                )
                task.result_data = result
                task.status = "done"
                task.progress = 100
                task.message = "done"

                # record usage
                pages = result.get("pages", 0)
                db.add(Usage(
                    tenant_id=tenant_id,
                    user_id=job.user_id,
                    job_id=job_id,
                    pages=pages,
                    statements=1,
                ))

            except Exception as exc:  # noqa: BLE001
                task.status = "error"
                task.error = f"{type(exc).__name__}: {exc}"
                task.message = task.error

            db.commit()

        # reload to check all tasks
        db.refresh(job)
        all_error = all(t.status == "error" for t in job.file_tasks)
        job.status = "error" if all_error else "done"
        db.commit()

    finally:
        db.close()

    purge()
