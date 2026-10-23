"""Test harness: SQLite instead of MySQL, Celery eager instead of Redis workers,
an in-memory Redis stand-in, and throwaway upload/output folders.

Settings are read at import time, so the environment is set before `app` loads.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
import time
from decimal import Decimal

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

_TMP = tempfile.mkdtemp(prefix="bsx_tests_")
os.environ.update({
    "BSX_ENV": "dev",
    "BSX_MYSQL_URL": "sqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/"),
    "BSX_UPLOAD_DIR": os.path.join(_TMP, "uploads"),
    "BSX_OUTPUT_DIR": os.path.join(_TMP, "output"),
    "BSX_REGISTRY_PATH": os.path.join(_TMP, "registry.json"),
    "BSX_JWT_SECRET": "test-secret-0123456789abcdef0123456789abcdef",
    # Celery in eager mode runs each task inside the request, so tests see the
    # result at once; local mode (threads) has its own tests in test_local_mode.py
    "BSX_QUEUE": "celery",
})


class FakeRedis:
    """The handful of Redis calls the app makes, kept in a dict."""

    def __init__(self):
        self.data: dict[str, object] = {}

    def ping(self):
        return True

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, seconds):
        return True

    def set(self, key, value, ex=None):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def delete(self, key):
        self.data.pop(key, None)

    def llen(self, key):
        return 0

    def scan_iter(self, pattern):
        prefix = pattern.rstrip("*")
        return [k for k in list(self.data) if k.startswith(prefix)]


from app import worker  # noqa: E402
from app.db.base import Base, engine  # noqa: E402

worker.celery_app.conf.task_always_eager = True
worker.celery_app.conf.task_eager_propagates = False


@pytest.fixture(autouse=True)
def fresh_state():
    """Every test starts with empty tables and an empty Redis."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    worker._redis = FakeRedis()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        yield c


_counter = [0]


def register(client, org="Test Lending Co") -> dict:
    """Create a tenant + admin user; return auth headers."""
    _counter[0] += 1
    email = f"user{_counter[0]}_{int(time.time() * 1000)}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "password123", "org_name": org,
                          "accept_terms": True})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_pdf(text: str | None) -> bytes:
    """A one-page PDF. With text it reads as digital; without, as scanned."""
    content = (f"BT /F1 10 Tf 20 700 Td ({text}) Tj ET" if text else "").encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


DIGITAL_TEXT = ("01-04-2023 NEFT PAYMENT RECEIVED FROM CUSTOMER ACCOUNT "
                "1,00,000.00 2,50,000.00 BALANCE 12345 67890")


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Replace the extraction engine: write a stub workbook (and the portal's
    analysis JSON, through the real builder), record each call."""
    import app.core.pipeline as pipeline
    from app.output import cam_json as cam

    calls = []

    def process(pdf_path, out_dir, password=None, use_ocr=True, dpi=300, backend=None,
                progress=None, source_name=None, bank=None, tenant_id=None, cam_json=False):
        calls.append({"path": pdf_path, "name": source_name, "tenant_id": tenant_id})
        if source_name and source_name.startswith("bad"):
            raise RuntimeError("no transaction table found in this PDF")
        if progress:
            progress(50, "halfway")
        os.makedirs(out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        out = os.path.join(out_dir, f"{stem}.xlsx")
        with open(out, "wb") as fh:
            fh.write(b"PK stub workbook")
        cam_out = cam.write(os.path.join(out_dir, f"{stem}.cam.json"),
                            cam.build(FAKE_PROFILE, [(1, "BREAK diff=5.00")], "words", "asis"))             if cam_json else None
        return {"xlsx": out, "cam_json": cam_out, "filename": os.path.basename(out), "rows": 12, "chain": 1.0,
                "flagged": 0, "pages": 1, "is_partial": False, "completeness": "COMPLETE",
                "financial_profile": {"credit_score_index": 60.0, "risk_rating": "B",
                                      "account_number": "50100012345678"},
                "info": {"bank": "Test Bank", "customer_name": "not for history"}}

    monkeypatch.setattr(pipeline, "process", process)
    return calls


FAKE_PROFILE = {
    "executive_summary": {
        "account_holder": "Test Traders", "bank_name": "Test Bank",
        "account_number": "50100012345678", "credit_score_index": 60.0, "risk_rating": "B",
        "scorecard_breakdown": {"cashflow_margin_score": 12.0, "liquidity_abb_score": None},
        "unscored_reasons": {"liquidity_abb_score": "OD limit not printed in statement"},
        "abb": 125000.5, "strengths": ["Regular inflows"], "red_flags": [],
    },
    "cash_flow": {"monthly_summary": [{"month": "2023-04", "inflow": 100000.0,
                                       "outflow": 80000.0, "net_flow": 20000.0}]},
    "account_health": {"monthly_health": [{"month": "2023-04", "abb": 125000.5,
                                           "closing_balance": 250000.0}]},
    "eligible_income": {"months_count": 2.0, "eligible_categories": [
        {"category": "Business Receipts", "count": 3, "amount": 90000.0},
        {"category": "Salary / Payroll", "count": 0, "amount": 0}]},
    "annotated_transactions": [
        {"txn_date": dt.date(2023, 4, 1), "narration": "NEFT FROM CUSTOMER",
         "credit": Decimal("100000.00"), "debit": None, "balance": Decimal("250000.00"),
         "category": "BUSINESS_REVENUE", "counterparty": "Customer", "page": 1},
        {"txn_date": dt.date(2023, 4, 2), "narration": "CHQ PAID",
         "credit": None, "debit": Decimal("80000.00"), "balance": Decimal("170000.00"), "page": 1},
        {"txn_date": dt.date(2023, 4, 3), "narration": "IMPS FROM 50100012345678", "credit": None,
         "debit": Decimal("100.00"), "balance": Decimal("169900.00"), "page": 2},
    ],
}
