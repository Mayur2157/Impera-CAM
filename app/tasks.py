"""Worker tasks. One task per uploaded file; see app/worker.py for the queues."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import pdfplumber

from . import jobs, storage
from .config import settings
from .core.classify import classify_page
from .db.base import SessionLocal
from .db.models import FileTask, Job, Usage
from .secretbox import unseal
from .worker import QUEUE_CPU, QUEUE_OCR, celery_app

log = logging.getLogger("bsx.tasks")


def dispatch(file_task_id: str, sealed_password: str | None, ocr: bool = False) -> None:
    """Enqueue one file. Each queue gets its own time limits."""
    if ocr:
        soft, hard, queue = settings.task_ocr_soft_seconds, settings.task_ocr_hard_seconds, QUEUE_OCR
    else:
        soft, hard, queue = settings.task_cpu_soft_seconds, settings.task_cpu_hard_seconds, QUEUE_CPU
    process_file.apply_async(args=[file_task_id, sealed_password, ocr], queue=queue,
                             soft_time_limit=soft, time_limit=hard)


def _has_scanned_pages(path: str, password: str | None) -> bool:
    # the same per-page test extraction uses (app/core/extract.words_for_page)
    with pdfplumber.open(path, password=password) as pdf:
        return any(classify_page(p, i).scanned for i, p in enumerate(pdf.pages, 1))


def _set(task_id: str, **fields) -> None:
    db = SessionLocal()
    try:
        t = db.query(FileTask).filter(FileTask.id == task_id).first()
        if t:
            for k, v in fields.items():
                setattr(t, k, v)
            db.commit()
    finally:
        db.close()


@celery_app.task(name="bsx.process_file")
def process_file(file_task_id: str, sealed_password: str | None = None, ocr: bool = False):
    from .core.pipeline import process as run_pipeline

    db = SessionLocal()
    try:
        task = db.query(FileTask).filter(FileTask.id == file_task_id).first()
        if task is None or task.status == "done":
            return          # purged, or a redelivery of a file already finished
        job = db.query(Job).filter(Job.id == task.job_id).first()
        job_id, tenant_id, user_id = job.id, job.tenant_id, job.user_id
        use_ocr, dpi, bank = job.use_ocr, job.dpi, job.bank
        name, pdf_path = task.name, storage.upload_path(task.path)
    finally:
        db.close()

    t0 = time.perf_counter()
    try:
        password = unseal(sealed_password)
        if not pdf_path or not os.path.exists(pdf_path):
            raise RuntimeError("uploaded file is no longer available — resubmit the PDF")

        # a scanned page (often just the cover) sends the whole file to the GPU queue
        if not ocr and use_ocr and _has_scanned_pages(pdf_path, password):
            _set(file_task_id, message="waiting for OCR worker")
            dispatch(file_task_id, sealed_password, ocr=True)
            log.info("routed file=%s job=%s to ocr", file_task_id, job_id)
            return

        _set(file_task_id, status="running", message="starting", started_at=datetime.utcnow())
        _finalize(job_id)

        def report(pct: int, msg: str):
            _set(file_task_id, progress=pct, message=msg)

        out_dir = os.path.join(settings.output_dir, tenant_id)   # tenant-scoped
        result = run_pipeline(pdf_path, out_dir, password=password, use_ocr=use_ocr,
                              dpi=dpi, progress=report, source_name=name, bank=bank,
                              tenant_id=tenant_id)
        result["xlsx"] = storage.output_rel(result["xlsx"])

        # result, status and the billing row land in one commit, so a
        # redelivered task can never meter the same file twice
        db = SessionLocal()
        try:
            t = db.query(FileTask).filter(FileTask.id == file_task_id).first()
            t.result_data = result
            t.status, t.progress, t.message = "done", 100, "done"
            t.finished_at = datetime.utcnow()
            db.add(Usage(tenant_id=tenant_id, user_id=user_id, job_id=job_id,
                         pages=result.get("pages", 0), statements=1))
            db.commit()
        finally:
            db.close()
        status = "done"
    except Exception as exc:                               # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        _set(file_task_id, status="error", error=error, message=error,
             finished_at=datetime.utcnow())
        status = "error"
    log.info("file=%s job=%s tenant=%s queue=%s status=%s seconds=%.2f",
             file_task_id, job_id, tenant_id, QUEUE_OCR if ocr else QUEUE_CPU,
             status, time.perf_counter() - t0)
    _finalize(job_id)


def _finalize(job_id: str) -> None:
    db = SessionLocal()
    try:
        jobs.finalize(db, job_id)
    finally:
        db.close()


@celery_app.task(name="bsx.purge")
def purge():
    removed = jobs.purge()
    log.info("purge jobs=%d files=%d", removed["jobs"], removed["files"])


@celery_app.task(name="bsx.reap_stuck")
def reap_stuck():
    n = jobs.reap_stuck()
    if n:
        log.warning("reaped %d stuck file(s)", n)
