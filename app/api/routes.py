"""HTTP surface — every route except /api/health requires a valid JWT.

POST /api/jobs                      upload PDFs, start a job
GET  /api/jobs                      list this tenant's jobs (history)
GET  /api/jobs/{id}                 poll status
GET  /api/jobs/{id}/download/{idx}  download the workbook (tenant-gated)
GET  /api/health                    server, database, queue and worker status
"""
from __future__ import annotations

import os
import re
import uuid

import pdfplumber
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text

from ..auth.auth import get_current_user
from ..config import settings
from ..db.base import SessionLocal
from ..db.models import User
from .. import jobs, storage
from ..worker import QUEUE_CPU, QUEUE_OCR, live_workers, redis_client

router = APIRouter(prefix="/api")

_CHUNK = 1 << 20


@router.get("/health")
def health():
    out = {"status": "ok", "db": "ok", "redis": "ok", "queues": {}, "workers": {}}
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:                                      # noqa: BLE001
        out["db"] = "unavailable"
    workers = []
    try:
        r = redis_client()
        r.ping()
        # the Redis transport keeps each queue as a list named after it
        out["queues"] = {q: r.llen(q) for q in (QUEUE_CPU, QUEUE_OCR)}
        workers = live_workers()
    except Exception:                                      # noqa: BLE001
        out["redis"] = "unavailable"
    out["workers"] = {q: sum(1 for w in workers if q in w.get("queues", []))
                      for q in (QUEUE_CPU, QUEUE_OCR)}
    if out["db"] != "ok" or out["redis"] != "ok":
        out["status"] = "degraded"

    # OCR runs on the workers now, so report what the live OCR worker found
    ocr = next((w["ocr"] for w in workers if QUEUE_OCR in w.get("queues", []) and w.get("ocr")), None)
    out.update({
        "ocr_backend": (ocr or {}).get("backend"),
        "ocr_device": (ocr or {}).get("device"),
        "gpu": (ocr or {}).get("gpu"),
        "cuda_compiled": (ocr or {}).get("cuda_compiled", False),
        "ocr_warning": (ocr or {}).get("warning") if ocr else
            "No OCR worker is online — scanned statements will wait in the queue.",
    })
    return out


def _save_upload(f: UploadFile, folder: str, limit: int, max_mb: int) -> tuple[str, str]:
    """Stream one upload to disk under the size cap; check it is a PDF."""
    if not (f.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, f"{f.filename}: only PDF files are accepted")
    safe = re.sub(r"\s+", "_", os.path.basename(f.filename).replace("/", "_"))
    path = os.path.join(folder, f"{uuid.uuid4().hex[:8]}_{safe}")
    size = 0
    with open(path, "wb") as fh:
        head = f.file.read(5)
        if head != b"%PDF-":
            fh.close()
            storage.remove_quietly(path)
            raise HTTPException(400, f"{f.filename}: not a PDF file")
        fh.write(head)
        size = len(head)
        while chunk := f.file.read(_CHUNK):
            size += len(chunk)
            if size > limit:
                fh.close()
                storage.remove_quietly(path)
                raise HTTPException(400, f"{f.filename} exceeds the {max_mb} MB limit")
            fh.write(chunk)
    return safe, path


def _check_opens(path: str, name: str, password: str | None) -> None:
    """Catch a wrong password now, not minutes later in a worker."""
    try:
        with pdfplumber.open(path, password=password or "") as pdf:
            if not pdf.pages:
                raise HTTPException(400, f"{name}: the PDF has no pages")
    except HTTPException:
        raise
    except Exception:                                      # noqa: BLE001
        msg = "wrong or missing PDF password" if password is not None else \
              "the PDF is password-protected or unreadable — enter its password"
        raise HTTPException(400, f"{name}: {msg}")


def submit_job(files: list[UploadFile], password: str | None, use_ocr: bool, dpi: int,
               bank: str | None, user: User, tenant, api_key_id: str | None = None) -> dict:
    """Check, save and enqueue an upload; shared by /api/jobs and /api/v1/jobs."""
    if tenant is not None and tenant.status == "suspended":
        raise HTTPException(403, "your organisation is suspended — it is read-only until reinstated")
    if not files:
        raise HTTPException(400, "no files uploaded")
    if dpi not in (200, 300, 400):
        raise HTTPException(400, "dpi must be 200, 300 or 400")

    max_files = tenant.max_files if tenant else settings.max_files
    max_mb = tenant.max_upload_mb if tenant else settings.max_upload_mb

    if len(files) > max_files:
        raise HTTPException(400, f"your plan allows at most {max_files} files per job")

    # fairness: one tenant cannot fill every worker
    active = jobs.active_files(user.tenant_id)
    if active + len(files) > settings.tenant_max_active_files:
        raise HTTPException(429, f"{active} of your files are still processing — "
                                 "wait for them to finish before uploading more")

    tenant_upload = os.path.join(settings.upload_dir, user.tenant_id)
    os.makedirs(tenant_upload, exist_ok=True)

    password = password or None
    saved: list[tuple[str, str]] = []
    try:
        for f in files:
            name, path = _save_upload(f, tenant_upload, max_mb * 1024 * 1024, max_mb)
            saved.append((name, path))
            _check_opens(path, name, password)
    except HTTPException:
        for _name, path in saved:          # nothing half-uploaded is left behind
            storage.remove_quietly(path)
        raise

    try:
        job_id = jobs.create(saved, tenant_id=user.tenant_id, user_id=user.id,
                             password=password, use_ocr=use_ocr, dpi=dpi,
                             bank=(bank or "").strip() or None, api_key_id=api_key_id)
    except jobs.QueueUnavailable:
        raise HTTPException(503, "the processing queue is unavailable — try again shortly")
    return {"job_id": job_id, "files": len(saved)}


# a plain def: FastAPI runs it in its threadpool, so file I/O never blocks the event loop
@router.post("/jobs", status_code=201)
def create_job(
    files: list[UploadFile] = File(...),
    password: str | None = Form(None),
    use_ocr: bool = Form(True),
    dpi: int = Form(300),
    bank: str | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    return submit_job(files, password, use_ocr, dpi, bank, current_user, current_user.tenant)


@router.get("/jobs")
def list_jobs(limit: int = 50, current_user: User = Depends(get_current_user)):
    """Return the most recent jobs for this tenant (newest first)."""
    return jobs.list_for_tenant(current_user.tenant_id, limit=max(1, min(limit, 100)))


@router.get("/jobs/{job_id}")
def job_status(job_id: str, current_user: User = Depends(get_current_user)):
    job = jobs.get(job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job


@router.get("/jobs/{job_id}/download/{index}")
def download(job_id: str, index: int, current_user: User = Depends(get_current_user)):
    found = jobs.file_for_download(job_id, current_user.tenant_id, index)
    if found is None:
        raise HTTPException(404, "unknown job")
    status, result = found
    if status == "missing":
        raise HTTPException(404, "no such file in this job")
    if status != "done" or not result:
        raise HTTPException(409, "that file is not ready yet")

    path = storage.output_path(result.get("xlsx"))
    if not path or not os.path.exists(path):
        raise HTTPException(410, "output has been cleaned up — resubmit the PDF")

    return FileResponse(
        path,
        filename=result.get("filename"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
