"""HTTP surface — all routes require a valid JWT.

POST /api/jobs                      upload PDFs, start a job
GET  /api/jobs                      list this tenant's jobs (history)
GET  /api/jobs/{id}                 poll status
GET  /api/jobs/{id}/download/{idx}  download the workbook (tenant-gated)
GET  /api/health                    server + OCR status
"""
from __future__ import annotations

import os
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..auth.auth import get_current_user
from ..config import settings
from ..db.models import User
from .. import jobs
from ..core import ocr

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    p = ocr.probe()
    return {
        "status": "ok",
        "ocr_backend": p["backend"],
        "ocr_device": p["device"],
        "gpu": p["gpu"],
        "cuda_compiled": p["cuda_compiled"],
        "ocr_warning": p["warning"],
        "workers": settings.workers,
    }


@router.post("/jobs", status_code=201)
async def create_job(
    files: list[UploadFile] = File(...),
    password: str | None = Form(None),
    use_ocr: bool = Form(True),
    dpi: int = Form(300),
    bank: str | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "no files uploaded")

    tenant = current_user.tenant
    max_files = tenant.max_files if tenant else settings.max_files
    max_mb = tenant.max_upload_mb if tenant else settings.max_upload_mb

    if len(files) > max_files:
        raise HTTPException(400, f"your plan allows at most {max_files} files per job")

    saved: list[tuple[str, str]] = []
    limit = max_mb * 1024 * 1024

    # Tenant-scoped upload directory
    tenant_upload = os.path.join(settings.upload_dir, current_user.tenant_id)
    os.makedirs(tenant_upload, exist_ok=True)

    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"{f.filename}: only PDF files are accepted")
        blob = await f.read()
        if len(blob) > limit:
            raise HTTPException(400, f"{f.filename} exceeds the {max_mb} MB limit")
        safe = re.sub(r"\s+", "_", os.path.basename(f.filename).replace("/", "_"))
        path = os.path.join(tenant_upload, f"{uuid.uuid4().hex[:8]}_{safe}")
        with open(path, "wb") as fh:
            fh.write(blob)
        saved.append((safe, path))

    job = jobs.create(
        saved,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        password=password or None,
        use_ocr=use_ocr,
        dpi=dpi,
        bank=(bank or "").strip() or None,
    )
    return {"job_id": job.id, "files": len(saved)}


@router.get("/jobs")
def list_jobs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Return the most recent jobs for this tenant (newest first)."""
    job_list = jobs.list_for_tenant(current_user.tenant_id, limit=limit)
    return [jobs.job_to_dict(j) for j in job_list]


@router.get("/jobs/{job_id}")
def job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    job = jobs.get(job_id)
    if job is None or job.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "unknown job")
    return jobs.job_to_dict(job)


@router.get("/jobs/{job_id}/download/{index}")
def download(
    job_id: str,
    index: int,
    current_user: User = Depends(get_current_user),
):
    job = jobs.get(job_id)
    if job is None or job.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "unknown job")

    tasks = job.file_tasks
    if index < 0 or index >= len(tasks):
        raise HTTPException(404, "no such file in this job")

    task = tasks[index]
    if task.status != "done" or not task.result_data:
        raise HTTPException(409, "that file is not ready yet")

    path = task.result_data.get("xlsx")
    if not path or not os.path.exists(path):
        raise HTTPException(410, "output has been cleaned up — resubmit the PDF")

    return FileResponse(
        path,
        filename=task.result_data.get("filename"),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
