"""Memory of account holders across statements — per-tenant MySQL store.

When ``tenant_id`` is supplied (web / SaaS path) all reads and writes go to
the ``account_registry`` table in MySQL, scoped to that tenant, so Customer A
can never see Customer B's data.

When ``tenant_id`` is ``None`` (CLI path / legacy) the old JSON file is used
unchanged so that ``python cli.py`` still works without a database.
"""
from __future__ import annotations

import json
import os
import re
import threading

from ..config import settings

_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _norm_phone(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    return d[-10:] if len(d) >= 10 else ""


def _norm_email(v) -> str:
    return str(v or "").strip().lower()


def _norm_address(v) -> str:
    """Street text without punctuation or spacing.  Short strings are ignored."""
    t = re.sub(r"[^A-Z0-9]", "", str(v or "").upper())
    return t if len(t) >= 20 else ""


def _identity(info: dict) -> dict:
    return {
        "account_number": re.sub(r"\D", "", str(info.get("account_number") or "")),
        "customer_name": str(info.get("customer_name") or ""),
        "bank": str(info.get("bank") or ""),
        "email": _norm_email(info.get("email")),
        "phone": _norm_phone(info.get("mobile")),
        "address": _norm_address(info.get("address")),
    }


# ---------------------------------------------------------------------------
# JSON fallback (CLI / no tenant context)
# ---------------------------------------------------------------------------

def _json_load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _json_linked(info: dict, path: str) -> list[dict]:
    me = _identity(info)
    out = []
    for acct, other in _json_load(path).items():
        if not acct or acct == me["account_number"]:
            continue
        shared = [k for k in ("email", "phone", "address")
                  if me[k] and me[k] == other.get(k)]
        if shared:
            out.append({
                "account_number": acct,
                "customer_name": other.get("customer_name", ""),
                "bank": other.get("bank", ""),
                "shared": shared,
            })
    return out


def _json_register(me: dict, path: str) -> None:
    with _LOCK:
        data = _json_load(path)
        data[me["account_number"]] = me
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
        os.replace(tmp, path)


# ---------------------------------------------------------------------------
# MySQL path (web / SaaS, tenant_id provided)
# ---------------------------------------------------------------------------

def _db_linked(me: dict, tenant_id: str) -> list[dict]:
    from ..db.base import SessionLocal
    from ..db.models import AccountRegistry

    db = SessionLocal()
    try:
        rows = db.query(AccountRegistry).filter(
            AccountRegistry.tenant_id == tenant_id,
            AccountRegistry.account_number != me["account_number"],
        ).all()

        out = []
        for row in rows:
            shared = [
                k for k in ("email", "phone", "address")
                if me[k] and me[k] == getattr(row, k, "")
            ]
            if shared:
                out.append({
                    "account_number": row.account_number,
                    "customer_name": row.customer_name or "",
                    "bank": row.bank or "",
                    "shared": shared,
                })
        return out
    finally:
        db.close()


def _db_register(me: dict, tenant_id: str) -> None:
    from sqlalchemy.exc import IntegrityError

    from ..db.base import SessionLocal
    from ..db.models import AccountRegistry

    fields = {k: me[k] for k in ("customer_name", "bank", "email", "phone", "address")}
    db = SessionLocal()
    try:
        # Workers run in parallel, and one upload often carries several months
        # of the same account: two of them can both miss the row and insert.
        # The unique (tenant, account) constraint decides; the loser updates.
        for _attempt in range(2):
            row = db.query(AccountRegistry).filter_by(
                tenant_id=tenant_id, account_number=me["account_number"]
            ).first()
            if row:
                for k, v in fields.items():
                    setattr(row, k, v)
            else:
                db.add(AccountRegistry(tenant_id=tenant_id,
                                       account_number=me["account_number"], **fields))
            try:
                db.commit()
                return
            except IntegrityError:
                db.rollback()
        raise RuntimeError("account registry write kept conflicting")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def linked_accounts(
    info: dict,
    path: str | None = None,
    tenant_id: str | None = None,
) -> list[dict]:
    """Return known accounts whose holder shares this holder's email/mobile/address."""
    me = _identity(info)
    if tenant_id:
        return _db_linked(me, tenant_id)
    # CLI / legacy fallback
    return _json_linked(info, path or settings.registry_path)


def register(
    info: dict,
    path: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Remember this account holder for future cross-statement linking."""
    me = _identity(info)
    if not me["account_number"] or not (me["email"] or me["phone"] or me["address"]):
        return          # nothing to match on

    if tenant_id:
        _db_register(me, tenant_id)
    else:
        _json_register(me, path or settings.registry_path)
