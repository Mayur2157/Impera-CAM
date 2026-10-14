#!/usr/bin/env python3
"""Report the staleness of every tracked reference. Exit 1 if legal content is overdue."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

REG = Path(__file__).resolve().parent.parent / "config" / "freshness.json"


def main() -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    today = date.today()
    blocking = 0

    print(f"Freshness report — {today}\n")
    for e in sorted(reg["entries"], key=lambda x: x["id"]):
        last = datetime.strptime(e["last_verified"], "%Y-%m-%d").date()
        due = last + timedelta(days=e["review_interval_days"])
        left = (due - today).days
        if left < 0:
            mark, note = ("BLOCKING" if e["kind"] == "legal" else "STALE"), f"{-left}d overdue"
            blocking += e["kind"] == "legal"
        elif left <= 14:
            mark, note = "DUE SOON", f"{left}d left"
        else:
            mark, note = "OK", f"{left}d left"
        print(f"  [{mark:>8}] {e['id']:<22} {e['kind']:<9} verified {e['last_verified']}  ({note})")
        if left <= 14:
            for src in e["authoritative_sources"]:
                print(f"             verify against: {src}")
            if e.get("notes"):
                print(f"             note: {e['notes']}")

    print()
    if blocking:
        print("Legal content is overdue. Re-verify against authoritative sources before")
        print("relying on it, then update last_verified in .agents/config/freshness.json.")
        return 1
    print("After re-verifying, update last_verified in .agents/config/freshness.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
