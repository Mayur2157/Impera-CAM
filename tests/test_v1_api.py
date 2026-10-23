"""/api/v1 — jobs, the CAM as JSON, transactions, download, API keys, usage."""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

from conftest import DIGITAL_TEXT, make_pdf, register

PDF = make_pdf(DIGITAL_TEXT)


def upload(client, headers, *names):
    files = [("files", (n, PDF, "application/pdf")) for n in names]
    return client.post("/api/v1/jobs", headers=headers, files=files)


def tenant_of(client, headers) -> str:
    return client.get("/api/auth/me", headers=headers).json()["tenant_id"]


def make_key(tenant_id: str, scopes=("jobs:read", "jobs:write"), name="Loan system") -> dict:
    """An API key as the (later) key endpoint will store it; returns the header."""
    from app.auth.principal import KEY_PREFIX, hash_key
    from app.db.base import SessionLocal
    from app.db.models import ApiKey, User

    secret = KEY_PREFIX + secrets.token_urlsafe(30)
    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.tenant_id == tenant_id).first()
        db.add(ApiKey(tenant_id=tenant_id, created_by=owner.id, name=name,
                      prefix=secret[:14], key_hash=hash_key(secret), scopes=list(scopes)))
        db.commit()
    finally:
        db.close()
    return {"X-API-Key": secret}


def set_row(model, row_id, **fields):
    from app.db.base import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(model).filter(model.id == row_id).first()
        for k, v in fields.items():
            setattr(row, k, v)
        db.commit()
    finally:
        db.close()


def test_jobs_result_transactions_download(client, fake_pipeline):
    h = register(client)
    r = upload(client, h, "a.pdf", "b.pdf")
    assert r.status_code == 201, r.text
    job_id = r.json()["job_id"]

    page = client.get("/api/v1/jobs?limit=1&offset=0", headers=h).json()
    assert page["total"] == 1 and page["items"][0]["id"] == job_id
    summary = page["items"][0]["files"][0]["result"]
    assert summary["score"] == 60.0 and summary["risk_rating"] == "B"

    job = client.get(f"/api/v1/jobs/{job_id}", headers=h).json()
    assert job["status"] == "done"
    result = job["files"][0]["result"]
    assert "financial_profile" not in result and "cam_json" not in result   # summaries only

    cam = client.get(f"/api/v1/jobs/{job_id}/files/0/result", headers=h).json()
    assert cam["file"]["rows"] == 12
    assert cam["account"]["account_number_masked"] == "XXXXXXXXXX5678"
    assert "50100012345678" not in str(cam)                                  # never unmasked
    assert cam["score"]["scorecard_breakdown"]["liquidity_abb_score"] is None
    assert cam["score"]["max_points"]["cashflow_margin_score"] == 20
    assert cam["monthly"] == [{"month": "2023-04", "inflow": 100000.0, "outflow": 80000.0,
                               "net": 20000.0, "closing_balance": 250000.0, "abb": 125000.5}]
    assert cam["income"]["eligible"] == [{"category": "Business Receipts", "count": 3,
                                          "amount": 90000.0, "monthly": 45000.0}]
    assert cam["validation"]["flagged_rows"] == [{"row": 2, "issue": "BREAK diff=5.00"}]
    assert "transactions" not in cam

    txns = client.get(f"/api/v1/jobs/{job_id}/files/0/transactions?offset=1&limit=1", headers=h).json()
    assert txns["total"] == 3
    assert txns["items"] == [{"sno": 2, "date": "2023-04-02", "value_date": None, "narration": "CHQ PAID",
                              "reference": None, "debit": 80000.0, "credit": None, "balance": 170000.0,
                              "category": "GENERAL_TRANSFER", "counterparty": "Unknown",
                              "status": "CHECK", "page": 1}]
    everything = client.get(f"/api/v1/jobs/{job_id}/files/0/transactions", headers=h).json()["items"]
    assert everything[2]["narration"] == "IMPS FROM XXXXXXXXXX5678"         # masked in narrations too

    dl = client.get(f"/api/v1/jobs/{job_id}/files/1/download", headers=h)
    assert dl.status_code == 200 and dl.content == b"PK stub workbook"
    assert client.get(f"/api/v1/jobs/{job_id}/files/2/result", headers=h).status_code == 404


def test_result_not_ready_and_expired(client, fake_pipeline, monkeypatch):
    from app import jobs, storage, tasks
    from app.db.base import SessionLocal
    from app.db.models import FileTask

    h = register(client)
    with monkeypatch.context() as m:
        m.setattr(tasks, "dispatch", lambda *a, **k: None)                # stays queued
        queued = upload(client, h, "q.pdf").json()["job_id"]
    assert client.get(f"/api/v1/jobs/{queued}/files/0/result", headers=h).status_code == 409

    done = upload(client, h, "d.pdf").json()["job_id"]
    db = SessionLocal()
    try:
        task = db.query(FileTask).filter(FileTask.job_id == done).one()
        os.remove(storage.output_path(task.result_data["cam_json"]))
    finally:
        db.close()
    assert client.get(f"/api/v1/jobs/{done}/files/0/result", headers=h).status_code == 410
    assert jobs.get(done, tenant_of(client, h)) is not None


def test_tenant_isolation(client, fake_pipeline):
    a, b = register(client, "Lender A"), register(client, "Lender B")
    job_id = upload(client, a, "a.pdf").json()["job_id"]
    for path in (f"/api/v1/jobs/{job_id}", f"/api/v1/jobs/{job_id}/files/0/result",
                 f"/api/v1/jobs/{job_id}/files/0/transactions", f"/api/v1/jobs/{job_id}/files/0/download"):
        assert client.get(path, headers=b).status_code == 404, path
    assert client.get("/api/v1/jobs", headers=b).json() == {"items": [], "total": 0}
    assert client.get("/api/v1/jobs").status_code == 401


def test_api_key_scopes_revoke_and_metering(client, fake_pipeline):
    from app.db.base import SessionLocal
    from app.db.models import ApiKey, Job

    h = register(client)
    tid = tenant_of(client, h)
    key = make_key(tid)
    r = upload(client, key, "api.pdf")
    assert r.status_code == 201, r.text
    job_id = r.json()["job_id"]
    assert client.get(f"/api/v1/jobs/{job_id}", headers=key).status_code == 200

    db = SessionLocal()
    try:
        stored = db.query(ApiKey).one()
        assert db.query(Job).filter(Job.id == job_id).one().api_key_id == stored.id
        assert stored.last_used_at is not None
        assert key["X-API-Key"] not in (stored.key_hash, stored.prefix)     # only a hash is kept
    finally:
        db.close()

    upload(client, h, "portal.pdf")
    usage = client.get("/api/v1/usage?group_by=api_key", headers=h).json()
    labels = {row["label"]: row["statements"] for row in usage["series"]}
    assert labels == {"Portal": 1, f"Loan system ({stored.prefix}…)": 1}

    read_only = make_key(tid, scopes=("jobs:read",), name="Reporting")
    assert upload(client, read_only, "x.pdf").status_code == 403
    assert client.get("/api/v1/jobs", headers=read_only).status_code == 200

    set_row(ApiKey, stored.id, revoked_at=datetime.utcnow())
    assert client.get("/api/v1/jobs", headers=key).status_code == 401
    assert client.get("/api/v1/jobs", headers={"X-API-Key": "icam_live_nope"}).status_code == 401
    # keys work on jobs only, not on portal routes
    assert client.get("/api/v1/usage", headers=read_only).status_code == 401


def test_suspended_tenant_is_read_only(client, fake_pipeline):
    from app.db.models import Tenant

    h = register(client)
    tid = tenant_of(client, h)
    key = make_key(tid)
    job_id = upload(client, h, "a.pdf").json()["job_id"]
    set_row(Tenant, tid, status="suspended")

    assert upload(client, h, "b.pdf").status_code == 403
    assert client.get(f"/api/v1/jobs/{job_id}/files/0/result", headers=h).status_code == 200
    assert client.get("/api/v1/jobs", headers=key).status_code == 403
    assert client.get("/api/auth/me", headers=h).json()["org_status"] == "suspended"


def test_api_key_rate_limited(client, fake_pipeline, monkeypatch):
    import dataclasses

    from app.auth import principal

    monkeypatch.setattr(principal, "settings",
                        dataclasses.replace(principal.settings, api_key_per_minute=2))
    h = register(client)
    key = make_key(tenant_of(client, h))
    codes = [client.get("/api/v1/jobs", headers=key).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_usage_by_day_and_user(client, fake_pipeline):
    from app.db.base import SessionLocal
    from app.db.models import Usage

    h = register(client)
    upload(client, h, "a.pdf", "b.pdf")
    tid = tenant_of(client, h)
    db = SessionLocal()
    try:   # an older statement, outside a 7-day window
        old = db.query(Usage).filter(Usage.tenant_id == tid).first()
        old.created_at = datetime.utcnow() - timedelta(days=10)
        db.commit()
    finally:
        db.close()

    today = datetime.utcnow().date()
    week = client.get(f"/api/v1/usage?from={today - timedelta(days=6)}&to={today}", headers=h).json()
    assert len(week["series"]) == 7 and week["series"][-1] == {
        "key": today.isoformat(), "label": today.isoformat(), "statements": 1, "pages": 1}
    assert week["totals"] == {"statements": 1, "pages": 1}
    assert week["plan"] == {"name": "free", "max_files_per_job": 10, "max_upload_mb": 20,
                            "monthly_statement_quota": None}

    month = client.get("/api/v1/usage?group_by=user", headers=h).json()
    assert month["totals"]["statements"] == 2
    assert [row["statements"] for row in month["series"]] == [2]

    assert client.get(f"/api/v1/usage?from={today}&to={today - timedelta(days=1)}",
                      headers=h).status_code == 400
    assert client.get("/api/v1/usage?group_by=week", headers=h).status_code == 422


def test_purge_removes_analysis_json(client, fake_pipeline):
    from app import jobs, storage
    from app.db.base import SessionLocal
    from app.db.models import FileTask, Job

    h = register(client)
    upload(client, h, "a.pdf")
    db = SessionLocal()
    try:
        cam_path = storage.output_path(db.query(FileTask).one().result_data["cam_json"])
        db.query(Job).update({Job.created_at: datetime.utcnow() - timedelta(days=2)})
        db.commit()
    finally:
        db.close()
    assert os.path.exists(cam_path)
    assert jobs.purge(max_age_seconds=3600)["jobs"] == 1
    assert not os.path.exists(cam_path)


def test_mask_account():
    from app.output.cam_json import mask_account

    assert mask_account("50100012345678") == "XXXXXXXXXX5678"
    assert mask_account("1234") == "XX34"
    assert mask_account("N/A") is None and mask_account(None) is None
