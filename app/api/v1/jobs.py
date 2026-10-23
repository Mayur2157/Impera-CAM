"""Statement jobs — for the portal (Bearer JWT) and customers' systems (X-API-Key).

POST /api/v1/jobs                                       upload PDFs, start a job
GET  /api/v1/jobs?limit&offset                          {items, total}, newest first
GET  /api/v1/jobs/{id}                                  status and per-file progress
GET  /api/v1/jobs/{id}/files/{i}/result                 the CAM as JSON
GET  /api/v1/jobs/{id}/files/{i}/transactions           the ledger, a page at a time
GET  /api/v1/jobs/{id}/files/{i}/download               the Excel workbook
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from ... import jobs, storage
from ...auth.principal import Principal, jobs_caller
from ...output import cam_json
from ..routes import submit_job

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

_read = jobs_caller("jobs:read")
_write = jobs_caller("jobs:write")

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _done_result(job_id: str, index: int, p: Principal) -> dict:
    """The finished file's stored result, or the contract's 404 / 409."""
    found = jobs.file_for_download(job_id, p.tenant_id, index)
    if found is None:
        raise HTTPException(404, "unknown job")
    status, result = found
    if status == "missing":
        raise HTTPException(404, "no such file in this job")
    if status != "done" or not result:
        raise HTTPException(409, "that file is not ready yet")
    return result


def _cam(result: dict) -> dict:
    path = storage.output_path(result.get("cam_json"))
    if not path or not os.path.exists(path):
        raise HTTPException(410, "the analysis has expired or predates the portal — resubmit the PDF")
    return cam_json.read(path)


# a plain def: FastAPI runs it in its threadpool, so file I/O never blocks the event loop
@router.post("", status_code=201)
def create_job(
    files: list[UploadFile] = File(...),
    password: str | None = Form(None),
    use_ocr: bool = Form(True),
    dpi: int = Form(300),
    bank: str | None = Form(None),
    p: Principal = Depends(_write),
):
    return submit_job(files, password, use_ocr, dpi, bank, p.user, p.tenant,
                      api_key_id=p.api_key.id if p.api_key else None)


@router.get("")
def list_jobs(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
              p: Principal = Depends(_read)):
    return jobs.page_for_tenant(p.tenant_id, limit=limit, offset=offset)


@router.get("/{job_id}")
def get_job(job_id: str, p: Principal = Depends(_read)):
    # per-file results are summaries; account details come only from /result
    job = jobs.get(job_id, p.tenant_id, full=False)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job


@router.get("/{job_id}/files/{index}/result")
def file_result(job_id: str, index: int, p: Principal = Depends(_read)):
    result = _done_result(job_id, index, p)
    cam = _cam(result)
    cam.pop("transactions", None)
    return {"file": jobs.file_summary(result), **cam}


@router.get("/{job_id}/files/{index}/transactions")
def file_transactions(job_id: str, index: int,
                      offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
                      p: Principal = Depends(_read)):
    txns = _cam(_done_result(job_id, index, p)).get("transactions") or []
    return {"items": txns[offset:offset + limit], "total": len(txns)}


@router.get("/{job_id}/files/{index}/download")
def download(job_id: str, index: int, p: Principal = Depends(_read)):
    result = _done_result(job_id, index, p)
    path = storage.output_path(result.get("xlsx"))
    if not path or not os.path.exists(path):
        raise HTTPException(410, "output has been cleaned up — resubmit the PDF")
    return FileResponse(path, filename=result.get("filename"), media_type=XLSX)
