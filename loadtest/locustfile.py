"""100 analysts using Impera CAM at once.

    set BSX_LOADTEST_PDFS=Bank\\*.pdf                      (local samples; never committed)
    locust -f loadtest/locustfile.py --headless -u 100 -r 10 -t 15m \
           --host http://localhost:8000 --csv loadtest/results/run

Each simulated user registers its own organisation, keeps the history list
fresh, uploads one statement roughly every ten minutes, polls with the same
1 s → 3 s backoff as the UI, and downloads the workbook. End-to-end time per
statement is reported as the "statement end-to-end" request.

Registration is rate limited per IP; for a load run from one machine raise
BSX_REGISTER_PER_HOUR and BSX_LOGIN_PER_MINUTE on the API first.
"""
from __future__ import annotations

import glob
import os
import random
import time
import uuid

from locust import HttpUser, between, events, task

PDFS = sorted(glob.glob(os.environ.get("BSX_LOADTEST_PDFS", "Bank/*.pdf")))
_BLOBS = {p: open(p, "rb").read() for p in PDFS}


@events.test_start.add_listener
def _check(environment, **_kw):
    if not PDFS:
        raise SystemExit("no PDFs found — set BSX_LOADTEST_PDFS to a glob of sample statements")


class Analyst(HttpUser):
    wait_time = between(20, 40)

    def on_start(self):
        email = f"load-{uuid.uuid4().hex[:12]}@example.com"
        r = self.client.post("/api/auth/register", name="/api/auth/register",
                             json={"email": email, "password": "load-test-pass",
                                   "org_name": "Load Test Lender"})
        token = r.json().get("access_token") if r.ok else None
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        # spread the first uploads over the opening minutes of the run
        self.next_upload = time.time() + random.uniform(0, 300)

    @task(3)
    def history(self):
        self.client.get("/api/jobs?limit=20", headers=self.headers, name="/api/jobs")

    @task(1)
    def health(self):
        self.client.get("/api/health", name="/api/health")

    @task(2)
    def maybe_upload(self):
        if time.time() < self.next_upload:
            return
        self.next_upload = time.time() + random.uniform(480, 720)
        path = random.choice(PDFS)
        started = time.perf_counter()
        r = self.client.post("/api/jobs", headers=self.headers, name="/api/jobs [upload]",
                             files=[("files", (os.path.basename(path), _BLOBS[path],
                                               "application/pdf"))])
        if not r.ok:
            return
        job_id = r.json()["job_id"]

        delay, status = 1.0, "queued"
        deadline = time.time() + 1800
        while time.time() < deadline:
            time.sleep(delay)
            s = self.client.get(f"/api/jobs/{job_id}", headers=self.headers,
                                name="/api/jobs/{id}")
            if not s.ok:
                break
            status = s.json()["status"]
            if status in ("done", "error"):
                break
            delay = min(delay * 1.5, 3.0)

        elapsed_ms = (time.perf_counter() - started) * 1000
        events.request.fire(request_type="E2E", name="statement end-to-end",
                            response_time=elapsed_ms, response_length=0,
                            exception=None if status == "done" else RuntimeError(status))
        if status == "done":
            self.client.get(f"/api/jobs/{job_id}/download/0", headers=self.headers,
                            name="/api/jobs/{id}/download")
