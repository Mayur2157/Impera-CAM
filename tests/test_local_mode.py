"""BSX_QUEUE=local: jobs on threads inside the API process, no Redis."""
from __future__ import annotations

import time

from conftest import DIGITAL_TEXT, make_pdf, register


def drain(tasks):
    """Wait for every local pool, including ones a running task creates (cpu → ocr)."""
    while tasks._pools:
        _queue, pool = tasks._pools.popitem()
        pool.shutdown(wait=True)


def upload(client, headers, name, content):
    return client.post("/api/v1/jobs", headers=headers,
                       files=[("files", (name, content, "application/pdf"))])


def test_local_threads_process_digital_and_scanned(client, fake_pipeline, monkeypatch):
    from app import tasks

    monkeypatch.setattr(tasks, "LOCAL", True)
    h = register(client)
    digital = upload(client, h, "digital.pdf", make_pdf(DIGITAL_TEXT)).json()["job_id"]
    scanned = upload(client, h, "scan.pdf", make_pdf(None)).json()["job_id"]
    drain(tasks)

    for job_id in (digital, scanned):
        job = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
        assert job["status"] == "done", job
    assert len(fake_pipeline) == 2          # the scan was handed to the OCR thread, run once


def test_local_threads_run_many_files_at_once(client, fake_pipeline, monkeypatch):
    """Several threads at once: the first local run lost a file to Celery's task
    wrapper, which is not thread-safe, and left it queued for ever."""
    from app import tasks

    monkeypatch.setattr(tasks, "LOCAL", True)
    h = register(client)
    files = [("files", (f"s{i}.pdf", make_pdf(DIGITAL_TEXT), "application/pdf")) for i in range(6)]
    job_id = client.post("/api/v1/jobs", headers=h, files=files).json()["job_id"]
    drain(tasks)
    job = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert [f["status"] for f in job["files"]] == ["done"] * 6


def test_local_crash_fails_the_file_instead_of_leaving_it_queued(client, fake_pipeline, monkeypatch):
    from app import tasks

    def boom(*_a, **_k):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(tasks, "LOCAL", True)
    monkeypatch.setattr(tasks, "run_file", boom)
    h = register(client)
    job_id = upload(client, h, "a.pdf", make_pdf(DIGITAL_TEXT)).json()["job_id"]
    drain(tasks)
    job = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert job["status"] == "error"
    assert "internal error" in job["files"][0]["error"]


def test_restart_fails_unfinished_files(client, fake_pipeline, monkeypatch):
    from app import jobs, tasks

    h = register(client)
    with monkeypatch.context() as m:
        m.setattr(tasks, "dispatch", lambda *a, **k: None)      # left waiting, as at a shutdown
        job_id = upload(client, h, "a.pdf", make_pdf(DIGITAL_TEXT)).json()["job_id"]
    assert jobs.fail_interrupted() == 1
    job = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert job["status"] == "error"
    assert "restarted" in job["files"][0]["error"]


def test_memory_store_counts_and_expires():
    from app.worker import MemoryStore

    m = MemoryStore()
    assert [m.incr("k"), m.incr("k")] == [1, 2]
    m.expire("k", 0.05)
    m.set("w:1", "x", ex=60)
    assert m.scan_iter("w:*") == ["w:1"]
    time.sleep(0.1)
    assert m.get("k") is None and m.incr("k") == 1


def test_portal_routes_and_api_404(client):
    import os

    from app.main import PORTAL

    if os.path.isdir(os.path.join(PORTAL, "assets")):
        assert "<div id=\"root\">" in client.get("/app/statements").text      # the SPA
        assert client.get("/api/v1/nope").status_code == 404                  # never the SPA
    assert client.get("/legacy").status_code == 200
