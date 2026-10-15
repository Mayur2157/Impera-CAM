"""The queued worker path must produce exactly what the pipeline produced before.

Runs the real engine over the local sample statements through
tasks.process_file and compares each result with tests/baseline/extraction.json
(keyed by PDF hash; see tests/baseline/make_baseline.py). Skipped when the
samples are not on this machine — they hold personal data and are never committed.
"""
from __future__ import annotations

import glob
import json
import os
import shutil

import pytest

from conftest import ROOT

sys_path = os.path.join(ROOT, "tests", "baseline")
SAMPLES = sorted(glob.glob(os.path.join(ROOT, "Bank", "*.pdf")))
BASELINE = os.path.join(sys_path, "extraction.json")

pytestmark = pytest.mark.skipif(not SAMPLES or not os.path.exists(BASELINE),
                                reason="local sample statements not present")


def test_worker_path_matches_baseline():
    import sys
    sys.path.insert(0, sys_path)
    from make_baseline import sha256, summarize

    from app import tasks
    from app.config import settings
    from app.db.base import SessionLocal
    from app.db.models import FileTask, Job, Tenant, User

    with open(BASELINE, encoding="utf-8") as fh:
        base = json.load(fh)

    db = SessionLocal()
    db.add(Tenant(id="baseline", name="baseline"))
    db.add(User(id="u", email="b@example.com", hashed_password="x", tenant_id="baseline"))
    job = Job(tenant_id="baseline", user_id="u", status="queued", use_ocr=True, dpi=300)
    db.add(job)
    db.flush()
    folder = os.path.join(settings.upload_dir, "baseline")
    os.makedirs(folder, exist_ok=True)
    ids = []
    for pos, src in enumerate(SAMPLES):
        dst = os.path.join(folder, os.path.basename(src))
        shutil.copyfile(src, dst)
        # the original name, as the baseline used it (it feeds bank-from-filename)
        t = FileTask(job_id=job.id, position=pos, name=os.path.basename(src),
                     path=os.path.relpath(dst, settings.upload_dir).replace(os.sep, "/"))
        db.add(t)
        db.flush()
        ids.append((t.id, sha256(src)))
    db.commit()
    db.close()

    # in sample order, so the account registry links accounts as the baseline did
    for tid, _key in ids:
        tasks.process_file(tid, None, False)

    db = SessionLocal()
    diffs = []
    for tid, key in ids:
        t = db.query(FileTask).filter(FileTask.id == tid).one()
        assert t.status == "done", t.error
        got = summarize(t.result_data)
        want = base[key]
        diffs += [f"{key[:12]}.{k}" for k in want if k != "seconds" and want[k] != got.get(k)]
    db.close()
    assert diffs == []
