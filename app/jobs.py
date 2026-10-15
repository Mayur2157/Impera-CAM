"""Job store — MySQL rows, processed by Celery workers (app/worker.py).

Architecture
------------
* The API writes Job + FileTask rows, then enqueues one task per file.
  Workers on any machine pick them up; a restart loses nothing queued.
* PDF passwords are NEVER persisted: each task message carries the password
  encrypted (app/secretbox.py) in Redis memory only.
* Everything returned to the API is serialised while its session is open,
  so routes never touch a detached ORM object.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from . import storage
from .config import settings
from .db.base import SessionLocal
from .db.models import FileTask, Job, Tenant

log = logging.getLogger("bsx.jobs")

ACTIVE = ("queued", "running")

# the fields the UI needs while listing history; the full result (financial
# profile, account details) is returned only for a single job
_SUMMARY_KEYS = ("rows", "chain", "flagged", "is_partial", "completeness", "filename")


class QueueUnavailable(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _result_for_client(result: dict | None, full: bool) -> dict | None:
    if not result:
        return result
    if full:
        # the stored path is internal; the client downloads by index
        return {k: v for k, v in result.items() if k != "xlsx"}
    out = {k: result.get(k) for k in _SUMMARY_KEYS}
    out["info"] = {"bank": (result.get("info") or {}).get("bank")}
    return out


def job_to_dict(job: Job, full: bool = True) -> dict:
    """Safe serialisation — password is never included. Call inside a session."""
    tasks = [{
        "id": t.id,
        "name": t.name,
        "status": t.status,
        "progress": t.progress,
        "message": t.message,
        "result": _result_for_client(t.result_data, full),
        "error": t.error,
    } for t in job.file_tasks]

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


# ---------------------------------------------------------------------------
# Public API (called from the routes)
# ---------------------------------------------------------------------------

def active_files(tenant_id: str) -> int:
    """Files of this tenant still waiting or running — the fairness cap counts these."""
    db = SessionLocal()
    try:
        return (db.query(func.count(FileTask.id))
                .join(Job, Job.id == FileTask.job_id)
                .filter(Job.tenant_id == tenant_id, FileTask.status.in_(ACTIVE))
                .scalar()) or 0
    finally:
        db.close()


def create(
    files: list[tuple[str, str]],
    tenant_id: str,
    user_id: str,
    password: str | None = None,
    use_ocr: bool = True,
    dpi: int = 300,
    bank: str | None = None,
) -> str:
    """Persist a job, enqueue one task per file, return the job id."""
    from .secretbox import seal
    from .tasks import dispatch

    db = SessionLocal()
    try:
        job = Job(tenant_id=tenant_id, user_id=user_id, status="queued",
                  use_ocr=use_ocr, dpi=dpi, bank=bank)
        db.add(job)
        db.flush()          # get job.id before tasks
        for pos, (name, path) in enumerate(files):
            db.add(FileTask(job_id=job.id, position=pos, name=name,
                            path=storage.upload_rel(path)))
        db.commit()
        job_id = job.id
        task_ids = [t.id for t in job.file_tasks]
    finally:
        db.close()

    sealed = seal(password)
    try:
        for tid in task_ids:
            dispatch(tid, sealed)
    except Exception as exc:                               # noqa: BLE001
        log.error("enqueue failed job=%s: %s", job_id, type(exc).__name__)
        _fail_job(job_id, "the processing queue is unavailable — try again shortly")
        raise QueueUnavailable(str(exc)) from exc
    return job_id


def get(job_id: str, tenant_id: str, full: bool = True) -> dict | None:
    """The job as a dict, or None when it is unknown or belongs to another tenant."""
    db = SessionLocal()
    try:
        job = (db.query(Job).options(selectinload(Job.file_tasks))
               .filter(Job.id == job_id).first())
        if job is None or job.tenant_id != tenant_id:
            return None
        return job_to_dict(job, full=full)
    finally:
        db.close()


def list_for_tenant(tenant_id: str, limit: int = 50) -> list[dict]:
    db = SessionLocal()
    try:
        jobs = (db.query(Job).options(selectinload(Job.file_tasks))
                .filter(Job.tenant_id == tenant_id)
                .order_by(Job.created_at.desc())
                .limit(limit).all())
        return [job_to_dict(j, full=False) for j in jobs]
    finally:
        db.close()


def file_for_download(job_id: str, tenant_id: str, index: int) -> tuple[str, dict | None] | None:
    """(status, result_data) of the index-th file, or None if not visible to this tenant."""
    db = SessionLocal()
    try:
        job = (db.query(Job).options(selectinload(Job.file_tasks))
               .filter(Job.id == job_id).first())
        if job is None or job.tenant_id != tenant_id:
            return None
        tasks = job.file_tasks
        if index < 0 or index >= len(tasks):
            return ("missing", None)
        return (tasks[index].status, tasks[index].result_data)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Job state (shared by the API and the workers)
# ---------------------------------------------------------------------------

def finalize(db, job_id: str) -> None:
    """Derive the job status from its files. Locks the job row so two workers
    finishing the last two files of one job cannot both miss the transition."""
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if job is None:
        return
    statuses = [s for (s,) in db.query(FileTask.status).filter(FileTask.job_id == job_id)]
    if any(s in ACTIVE for s in statuses):
        if job.status == "queued" and any(s != "queued" for s in statuses):
            job.status = "running"
    else:
        job.status = "error" if statuses and all(s == "error" for s in statuses) else "done"
    db.commit()


def _fail_job(job_id: str, message: str) -> None:
    db = SessionLocal()
    try:
        for t in db.query(FileTask).filter(FileTask.job_id == job_id,
                                           FileTask.status.in_(ACTIVE)):
            t.status, t.error, t.message = "error", message, message
        db.commit()
        finalize(db, job_id)
    finally:
        db.close()


def purge(max_age_seconds: int | None = None) -> dict:
    """Remove finished jobs past retention, their uploads and workbooks, and any
    stray file older than retention that no waiting or running task needs."""
    age = max_age_seconds or settings.retention_seconds
    cutoff = datetime.utcnow() - timedelta(seconds=age)
    jobs_removed = files_removed = 0

    db = SessionLocal()
    try:
        old = (db.query(Job).options(selectinload(Job.file_tasks))
               .filter(Job.created_at < cutoff, Job.status.in_(["done", "error"]))
               .all())
        for job in old:
            for task in job.file_tasks:
                storage.remove_quietly(storage.upload_path(task.path))
                storage.remove_quietly(storage.output_path((task.result_data or {}).get("xlsx")))
            db.delete(job)
            jobs_removed += 1
        db.commit()

        keep = {os.path.normcase(os.path.abspath(storage.upload_path(p)))
                for (p,) in db.query(FileTask.path).filter(FileTask.status.in_(ACTIVE))}
        tenant_ids = [tid for (tid,) in db.query(Tenant.id)]
    finally:
        db.close()

    # orphans: uploads of crashed jobs, workbooks of rows written before this
    # sweep. Only the per-tenant folders are swept — files the CLI writes to
    # the folder roots belong to the operator.
    limit = time.time() - age
    tenant_dirs = [os.path.join(base, tid)
                   for base in (settings.upload_dir, settings.output_dir) for tid in tenant_ids]
    for tdir in tenant_dirs:
        for root, _dirs, names in os.walk(tdir):
            for n in names:
                p = os.path.join(root, n)
                if n.startswith(".") or os.path.normcase(os.path.abspath(p)) in keep:
                    continue
                try:
                    if os.path.getmtime(p) < limit:
                        os.remove(p)
                        files_removed += 1
                except OSError:
                    pass
    return {"jobs": jobs_removed, "files": files_removed}


def reap_stuck() -> int:
    """Fail files still 'running' long after any worker would have killed them."""
    grace = settings.task_ocr_hard_seconds + 600
    cutoff = datetime.utcnow() - timedelta(seconds=grace)
    db = SessionLocal()
    try:
        stuck = (db.query(FileTask)
                 .filter(FileTask.status == "running", FileTask.started_at < cutoff)
                 .all())
        jobs = set()
        for t in stuck:
            t.status = "error"
            t.error = t.message = "processing timed out — resubmit the PDF"
            jobs.add(t.job_id)
        db.commit()
        for jid in jobs:
            finalize(db, jid)
        return len(stuck)
    finally:
        db.close()
