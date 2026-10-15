"""Job lifecycle through the API: upload → queue → worker → status → download."""
from __future__ import annotations

import dataclasses
import os
from datetime import datetime, timedelta

import pytest

from conftest import DIGITAL_TEXT, make_pdf, register

PDF = make_pdf(DIGITAL_TEXT)


def upload(client, headers, *names, data=None, content=PDF):
    files = [("files", (n, content, "application/pdf")) for n in names]
    return client.post("/api/jobs", headers=headers, files=files, data=data or {})


def test_job_lifecycle_and_download(client, fake_pipeline):
    h = register(client)
    r = upload(client, h, "stmt one.pdf", "stmt two.pdf")
    assert r.status_code == 201, r.text
    job_id = r.json()["job_id"]

    # status is served after the worker's session has closed (the old
    # detached-instance crash) and keeps upload order
    job = client.get(f"/api/jobs/{job_id}", headers=h).json()
    assert job["status"] == "done"
    assert [f["name"] for f in job["files"]] == ["stmt_one.pdf", "stmt_two.pdf"]
    assert job["files"][0]["result"]["rows"] == 12
    assert "xlsx" not in job["files"][0]["result"]          # internal path never leaves

    dl = client.get(f"/api/jobs/{job_id}/download/1", headers=h)
    assert dl.status_code == 200
    assert dl.content == b"PK stub workbook"
    assert client.get(f"/api/jobs/{job_id}/download/2", headers=h).status_code == 404


def test_history_is_summary_only(client, fake_pipeline):
    h = register(client)
    upload(client, h, "a.pdf")
    hist = client.get("/api/jobs", headers=h).json()
    result = hist[0]["files"][0]["result"]
    assert result["chain"] == 1.0 and result["info"] == {"bank": "Test Bank"}
    assert "financial_profile" not in result                # account details stay out of lists


def test_tenant_isolation(client, fake_pipeline):
    a, b = register(client, "Lender A"), register(client, "Lender B")
    job_id = upload(client, a, "a.pdf").json()["job_id"]
    assert client.get(f"/api/jobs/{job_id}", headers=b).status_code == 404
    assert client.get(f"/api/jobs/{job_id}/download/0", headers=b).status_code == 404
    assert client.get("/api/jobs", headers=b).json() == []


def test_partial_and_total_failure(client, fake_pipeline):
    h = register(client)
    mixed = upload(client, h, "good.pdf", "bad.pdf").json()["job_id"]
    job = client.get(f"/api/jobs/{mixed}", headers=h).json()
    assert job["status"] == "done"
    assert [f["status"] for f in job["files"]] == ["done", "error"]
    assert "no transaction table" in job["files"][1]["error"]

    failed = upload(client, h, "bad.pdf").json()["job_id"]
    assert client.get(f"/api/jobs/{failed}", headers=h).json()["status"] == "error"


def test_scanned_file_is_routed_to_ocr_queue(client, fake_pipeline, monkeypatch):
    from app import tasks

    seen = []
    real = tasks.dispatch
    monkeypatch.setattr(tasks, "dispatch",
                        lambda tid, pw, ocr=False: (seen.append(ocr), real(tid, pw, ocr)))
    h = register(client)
    upload(client, h, "scan.pdf", content=make_pdf(None))
    assert seen == [False, True]          # cpu first, then re-queued on ocr
    assert len(fake_pipeline) == 1        # processed once, by the ocr stage


def test_digital_file_stays_on_cpu(client, fake_pipeline, monkeypatch):
    from app import tasks

    seen = []
    real = tasks.dispatch
    monkeypatch.setattr(tasks, "dispatch",
                        lambda tid, pw, ocr=False: (seen.append(ocr), real(tid, pw, ocr)))
    upload(client, register(client), "digital.pdf")
    assert seen == [False]


@pytest.mark.parametrize("name,content,why", [
    ("notes.txt", PDF, "only PDF"),
    ("fake.pdf", b"hello, not a pdf at all", "not a PDF"),
])
def test_rejects_non_pdf(client, fake_pipeline, name, content, why):
    r = upload(client, register(client), name, content=content)
    assert r.status_code == 400 and why in r.json()["detail"]
    assert fake_pipeline == []


def test_bad_dpi_rejected(client, fake_pipeline):
    r = upload(client, register(client), "a.pdf", data={"dpi": "9999"})
    assert r.status_code == 400


def test_tenant_active_file_cap(client, fake_pipeline, monkeypatch):
    from app.api import routes
    from app.db.base import SessionLocal
    from app.db.models import FileTask, Job, User

    monkeypatch.setattr(routes, "settings",
                        dataclasses.replace(routes.settings, tenant_max_active_files=2))
    h = register(client)
    db = SessionLocal()
    user = db.query(User).first()
    job = Job(tenant_id=user.tenant_id, user_id=user.id, status="queued")
    db.add(job)
    db.flush()
    db.add(FileTask(job_id=job.id, name="waiting.pdf", path="x.pdf", status="queued"))
    db.commit()
    db.close()

    r = upload(client, h, "one.pdf", "two.pdf")
    assert r.status_code == 429


def test_queue_down_returns_503(client, fake_pipeline, monkeypatch):
    from app import tasks

    def boom(*_a, **_k):
        raise ConnectionError("redis down")

    monkeypatch.setattr(tasks, "dispatch", boom)
    h = register(client)
    r = upload(client, h, "a.pdf")
    assert r.status_code == 503
    job = client.get("/api/jobs", headers=h).json()[0]
    assert job["status"] == "error"


def test_purge_keeps_usage_and_operator_files(client, fake_pipeline):
    from app import jobs
    from app.config import settings
    from app.db.base import SessionLocal
    from app.db.models import Job, Usage

    h = register(client)
    job_id = upload(client, h, "old.pdf").json()["job_id"]
    operator_file = os.path.join(settings.output_dir, "cli_run.xlsx")
    with open(operator_file, "wb") as fh:
        fh.write(b"cli output")
    os.utime(operator_file, (0, 0))       # ancient, but not a tenant file

    db = SessionLocal()
    db.query(Job).filter(Job.id == job_id).update(
        {"created_at": datetime.utcnow() - timedelta(days=2)})
    db.commit()
    db.close()

    removed = jobs.purge(max_age_seconds=3600)
    assert removed["jobs"] == 1
    db = SessionLocal()
    assert db.query(Job).count() == 0
    assert db.query(Usage).count() == 1   # billing outlives the job
    db.close()
    assert os.path.exists(operator_file)
    assert client.get(f"/api/jobs/{job_id}", headers=h).status_code == 404


def test_reaper_fails_stuck_files(client):
    from app import jobs
    from app.db.base import SessionLocal
    from app.db.models import FileTask, Job, User

    register(client)
    db = SessionLocal()
    user = db.query(User).first()
    job = Job(tenant_id=user.tenant_id, user_id=user.id, status="running")
    db.add(job)
    db.flush()
    db.add(FileTask(job_id=job.id, name="stuck.pdf", path="x.pdf", status="running",
                    started_at=datetime.utcnow() - timedelta(days=1)))
    db.commit()
    job_id = job.id
    db.close()

    assert jobs.reap_stuck() == 1
    db = SessionLocal()
    assert db.query(Job).filter(Job.id == job_id).one().status == "error"
    db.close()


def test_health_reports_missing_ocr_worker(client):
    body = client.get("/api/health").json()
    assert body["db"] == "ok" and body["redis"] == "ok"
    assert body["workers"]["ocr"] == 0
    assert "No OCR worker" in body["ocr_warning"]
