#!/usr/bin/env python3
"""
Structural validation for the AI Rules & Skills pack.

Checks:
  1. Manifest and filesystem agree — no orphans, no missing files
  2. Rule frontmatter is complete and matches the manifest
  3. Every normative bullet is marked [H<n>] or [S<n>]; IDs are unique per file
  4. No duplicate content between .agents/ and generated adapters
  5. Generated adapters are not stale (delegates to sync.py --check)
  6. Every `freshness: tracked` file has a register entry, and none is past due
  7. No hardcoded vendor model identifiers outside config/defaults.md

    python3 .agents/scripts/validate.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS = ROOT / ".agents"

REQUIRED_FRONTMATTER = ["id", "title", "scope", "globs", "category", "version", "updated", "freshness"]
NORMATIVE = re.compile(r"^\s*[-*]\s+\*\*\[([HS])(\d+)\]\*\*")
BULLET = re.compile(r"^\s*[-*]\s+")
MODEL_LITERAL = re.compile(
    r"\b(gpt-[0-9][\w.-]*|claude-[a-z0-9][\w.-]*|gemini-[0-9][\w.-]*|"
    r"text-embedding-[0-9][\w.-]*|o[0-9]-[\w.-]+)\b"
)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def check_manifest_sync(m: dict) -> None:
    declared = {AGENTS / r["path"] for r in m["rules"]}
    on_disk = set((AGENTS / "rules").rglob("*.md"))
    for p in on_disk - declared:
        err(f"rule file not in manifest: {p.relative_to(ROOT)}")
    for p in declared - on_disk:
        err(f"manifest references a missing rule: {p.relative_to(ROOT)}")

    declared_skills = {AGENTS / s["path"] for s in m["skills"]}
    on_disk_skills = set((AGENTS / "skills").rglob("SKILL.md"))
    for p in on_disk_skills - declared_skills:
        err(f"skill not in manifest: {p.relative_to(ROOT)}")
    for p in declared_skills - on_disk_skills:
        err(f"manifest references a missing skill: {p.relative_to(ROOT)}")


def check_rules(m: dict) -> dict[str, str]:
    tracked: dict[str, str] = {}
    for rule in m["rules"]:
        path = AGENTS / rule["path"]
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        fm = frontmatter(text)

        for key in REQUIRED_FRONTMATTER:
            if key not in fm:
                err(f"{rel}: missing frontmatter key '{key}'")

        if fm.get("id") != rule["id"]:
            err(f"{rel}: frontmatter id '{fm.get('id')}' != manifest id '{rule['id']}'")
        if fm.get("scope") != rule["scope"]:
            err(f"{rel}: frontmatter scope '{fm.get('scope')}' != manifest scope '{rule['scope']}'")
        if rule["scope"] == "always" and rule["globs"]:
            err(f"{rel}: scope is always but manifest declares globs")
        if rule["scope"] == "glob" and not rule["globs"]:
            err(f"{rel}: scope is glob but manifest declares no globs")

        if fm.get("freshness") == "tracked":
            tracked[rule["id"]] = str(rel)
        elif fm.get("freshness") not in ("none", "tracked"):
            err(f"{rel}: freshness must be 'none' or 'tracked', got '{fm.get('freshness')}'")

        # Hard/soft marking + uniqueness
        seen: set[str] = set()
        in_normative = False
        has_hard = False
        for i, line in enumerate(text.splitlines(), 1):
            if line.startswith("## "):
                head = line.strip().lower()
                in_normative = head.startswith("## hard rules") or head.startswith("## soft defaults")
                continue
            match = NORMATIVE.match(line)
            if not match:
                if in_normative and BULLET.match(line):
                    err(f"{rel}:{i}: normative bullet is not marked [H<n>] or [S<n>]")
                continue
            ident = f"{match.group(1)}{match.group(2)}"
            if ident in seen:
                err(f"{rel}:{i}: duplicate identifier [{ident}]")
            seen.add(ident)
            has_hard = has_hard or match.group(1) == "H"

        if not has_hard:
            warn(f"{rel}: no hard rules — is this rule enforceable?")
    return tracked


def check_skills(m: dict) -> dict[str, str]:
    tracked: dict[str, str] = {}
    for skill in m["skills"]:
        path = AGENTS / skill["path"]
        fm = frontmatter(path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT)
        for key in ("name", "description"):
            if key not in fm:
                err(f"{rel}: missing frontmatter key '{key}'")
        if fm.get("name") != skill["id"]:
            err(f"{rel}: frontmatter name '{fm.get('name')}' != manifest id '{skill['id']}'")
        for ref in path.parent.glob("reference.md"):
            head = ref.read_text(encoding="utf-8")[:400]
            if "freshness: tracked" in head:
                tracked[skill["id"]] = str(ref.relative_to(ROOT))
    return tracked


def check_no_duplicate_content() -> None:
    """Every generated file must be a pointer, not a copy of canonical content."""
    canonical = {}
    for p in AGENTS.rglob("*.md"):
        canonical[hashlib.sha256(p.read_bytes()).hexdigest()] = p.relative_to(ROOT)

    generated_files: list[Path] = []
    for root in (ROOT / ".cursor", ROOT / ".claude"):
        if root.exists():
            generated_files.extend(p for p in root.rglob("*") if p.is_file())

    standalone = [
        ROOT / ".github" / "copilot-instructions.md",
        ROOT / ".windsurfrules",
        ROOT / ".clinerules",
    ]
    for s in standalone:
        if s.exists():
            generated_files.append(s)

    for p in generated_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(ROOT)
        if "GENERATED by .agents/scripts/sync.py" not in text:
            err(f"{rel}: generated file is missing its DO-NOT-EDIT banner")
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest in canonical:
            err(f"{rel}: byte-identical duplicate of {canonical[digest]}")
        if len(text.splitlines()) > 80:
            warn(f"{rel}: adapter is {len(text.splitlines())} lines — pointers "
                 "should be short; is content leaking into the generated tree?")


def check_adapters_current() -> None:
    result = subprocess.run(
        [sys.executable, str(AGENTS / "scripts" / "sync.py"), "--check"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        for line in result.stdout.strip().splitlines():
            err(f"adapter drift: {line}")


def check_freshness(tracked: dict[str, str]) -> None:
    reg_path = AGENTS / "config" / "freshness.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    entries = {e["id"]: e for e in reg["entries"]}
    covered = {c for e in reg["entries"] for c in e.get("covers", [])}
    today = date.today()

    for rid, rel in tracked.items():
        if rid not in entries and rid not in covered:
            err(f"{rel}: freshness is tracked but '{rid}' has no entry in config/freshness.json")

    for eid, entry in entries.items():
        last = datetime.strptime(entry["last_verified"], "%Y-%m-%d").date()
        due = last + timedelta(days=entry["review_interval_days"])
        if today > due:
            days = (today - due).days
            msg = (f"STALE: '{eid}' ({entry['kind']}) last verified {entry['last_verified']}, "
                   f"review was due {due} — {days} day(s) overdue")
            if entry["kind"] == "legal":
                err(msg + ". Legal content must be re-verified before use.")
            else:
                warn(msg)


def check_no_model_literals() -> None:
    allowed = AGENTS / "config" / "defaults.md"
    for p in list(AGENTS.rglob("*.md")):
        if p == allowed:
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for match in MODEL_LITERAL.finditer(line):
                warn(f"{p.relative_to(ROOT)}:{i}: vendor model identifier "
                     f"'{match.group(0)}' outside config/defaults.md")


def main() -> int:
    manifest = json.loads((AGENTS / "manifest.json").read_text(encoding="utf-8"))

    check_manifest_sync(manifest)
    tracked = check_rules(manifest)
    tracked.update(check_skills(manifest))
    check_no_duplicate_content()
    check_adapters_current()
    check_freshness(tracked)
    check_no_model_literals()

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print()
    print(f"{len(manifest['rules'])} rules, {len(manifest['skills'])} skills · "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
