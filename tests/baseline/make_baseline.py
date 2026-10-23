"""Record (or compare against) the extraction + scoring baseline for local samples.

    python tests/baseline/make_baseline.py "Bank/*.pdf"            # write baseline
    python tests/baseline/make_baseline.py "Bank/*.pdf" --check    # compare

Entries are keyed by the PDF's SHA-256, never by file or holder name, and hold
only non-personal metrics plus a digest of the full result, so any change in
what the pipeline returns is caught without storing personal data (rules H9).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

BASELINE = os.path.join(os.path.dirname(__file__), "extraction.json")

# keep the real JSON registry and output folder untouched
_TMP = tempfile.mkdtemp(prefix="bsx_baseline_")
os.environ.setdefault("BSX_REGISTRY_PATH", os.path.join(_TMP, "registry.json"))

from app.core.pipeline import process  # noqa: E402

PROFILE_KEYS = ("credit_score_index", "risk_rating", "foir_percentage", "dscr",
                "abb", "outward_bounces", "net_cash_flow")
RESULT_KEYS = ("rows", "chain", "mode", "strategy", "flagged", "reconstructed",
               "pages", "scanned_pages", "is_partial")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest(result: dict) -> str:
    """Hash of everything the pipeline returned except where it wrote the files."""
    body = {k: v for k, v in result.items() if k not in ("xlsx", "cam_json", "filename")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def summarize(result: dict) -> dict:
    fp = result.get("financial_profile") or {}
    out = {k: result.get(k) for k in RESULT_KEYS}
    out.update({f"profile.{k}": fp.get(k) for k in PROFILE_KEYS})
    out["digest"] = digest(result)
    return out


def run(pattern: str) -> dict:
    # each run starts from an empty registry so linked accounts are reproducible
    reg = os.environ["BSX_REGISTRY_PATH"]
    if os.path.exists(reg):
        os.remove(reg)
    out_dir = os.path.join(_TMP, "out")
    entries = {}
    for path in sorted(glob.glob(pattern)):
        t0 = time.perf_counter()
        try:
            r = process(path, out_dir, source_name=os.path.basename(path))
            entry = summarize(r)
        except Exception as exc:  # noqa: BLE001 — a failure is a baseline fact too
            entry = {"error": type(exc).__name__}
        entry["seconds"] = round(time.perf_counter() - t0, 2)
        entries[sha256(path)] = entry
        print(f"{entry.get('rows', '-')!s:>5} rows  chain={entry.get('chain', '-')}"
              f"  {entry['seconds']:6.2f}s  {sha256(path)[:12]}")
    return entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    entries = run(a.pattern)
    if not a.check:
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2, sort_keys=True)
        print(f"wrote {len(entries)} entries to {BASELINE}")
        return 0

    with open(BASELINE, encoding="utf-8") as fh:
        base = json.load(fh)
    bad = 0
    for key, want in base.items():
        got = entries.get(key)
        if got is None:
            print(f"MISSING {key[:12]}")
            bad += 1
            continue
        diffs = [k for k in want if k != "seconds" and want[k] != got.get(k)]
        if diffs:
            bad += 1
            print(f"CHANGED {key[:12]}: {', '.join(diffs)}")
    print("baseline OK" if not bad else f"{bad} statement(s) differ")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
