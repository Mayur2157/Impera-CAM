"""Who each transaction is with, kept apart from why it happened.

A counterparty's identity comes from its account number when one is printed,
otherwise from its name (spelling variants merged). The relationship to the
holder (own account, related party, lender, customer, vendor …) is decided
once per counterparty from all of its transactions, so one account is never
'related party' in one row and 'vendor' in the next. Each transaction keeps
its own purpose (its category): a related party can be paid a hiring charge
(an operating cost) and also receive an internal transfer (not a cost).
"""
from __future__ import annotations

import re
from collections import defaultdict

from .narration_rules import _ACCT_TOKEN, same_name_variant

_NO_ENTITY = {"Unknown", "Cash", "Bank", "Tax Authority", ""}

# what a transaction's category says about the party on the other side
_RELATION_OF = {
    "SELF_TRANSFER_CR": "SELF", "SELF_TRANSFER_DR": "SELF",
    "RELATED_PARTY_CR": "RELATED_PARTY", "RELATED_PARTY_DR": "RELATED_PARTY",
    "LOAN_EMI": "LENDER", "LOAN_DISBURSEMENT": "LENDER",
    "BANK_FUNDED_INFLOW": "BANK",
    "PAYROLL": "EMPLOYEE",
    "BUSINESS_RECEIPT": "CUSTOMER",
    "BUSINESS_EXPENSE": "VENDOR",
    "UNKNOWN_PERSONAL_CR": "INDIVIDUAL", "PERSONAL_LOAN_CR": "INDIVIDUAL", "PERSONAL_LOAN_DR": "INDIVIDUAL",
}
# identity evidence outranks trading evidence: an account the holder owns is
# theirs whatever a payment to it is for
_RANK = ["SELF", "RELATED_PARTY", "LENDER", "BANK", "EMPLOYEE", "INDIVIDUAL",
         "CUSTOMER & VENDOR", "CUSTOMER", "VENDOR"]


_LEGAL_SUFFIX = {"PVT", "PRIVATE", "LTD", "LIMITED", "LLP", "INC", "CO", "COMPANY", "CORP"}


def entity_key(counterparty: str) -> str | None:
    """'A/c 50200013789806' / 'Loan A/c …' → the account; a name → its words,
    upper-case, without an honorific in front or legal suffixes at the end.
    Initials stay: 'L T Ltd' is 'L T', not 'T'; 'K P Enterprises' keeps its P."""
    cp = (counterparty or "").strip()
    if cp in _NO_ENTITY:
        return None
    m = re.search(r"\bA/c\s*([A-Z0-9]+)", cp, re.I)
    if m:
        return f"A/C {m.group(1).upper()}"
    t = cp.upper().replace("&", " AND ")
    t = re.sub(r"^(?:M/S|MR|MRS|MS|SMT|DR)\b\.?", " ", t)
    words = re.sub(r"[^A-Z0-9 ]", " ", t).split()
    popped = False
    while len(words) > 1:
        w = words[-1]
        # a suffix, one cut short by the bank ('PRIVATE LIMI'), or the 'P' of 'P LTD'
        if w in _LEGAL_SUFFIX or (len(w) >= 3 and any(x.startswith(w) for x in _LEGAL_SUFFIX)) \
                or (w == "P" and popped):
            words.pop()
            popped = True
        else:
            break
    if words and words[0] == "THE" and len(words) > 1:
        words.pop(0)
    return " ".join(words) or None


def _initials(key: str) -> list[str]:
    return [w for w in key.split() if len(w) == 1]


def _same_entity(a: str, b: str) -> bool:
    """Spelling variants of one name, with the same initials ('K P' never
    merges with 'K M', nor 'L T' with a bare 'T')."""
    return _initials(a) == _initials(b) and same_name_variant(a, b)


def assign_entities(txns: list[dict]) -> dict[str, dict]:
    """Set `counterparty_id`, `relationship` and `relationship_basis` on every
    transaction; return {counterparty_id: summary}."""
    amount = defaultdict(float)
    for t in txns:
        k = entity_key(t.get("counterparty"))
        if k:
            amount[k] += float(t.get("credit") or t.get("debit") or 0)
    # spelling variants of one name join the largest one; account numbers stand alone
    canon: dict[str, str] = {}
    names: list[str] = []
    for k in sorted(amount, key=lambda x: -amount[x]):
        if k.startswith("A/C "):
            canon[k] = k
            continue
        canon[k] = next((n for n in names if _same_entity(k, n)), k)
        if canon[k] == k:
            names.append(k)

    rows = defaultdict(list)
    for t in txns:
        t.setdefault("purpose", purpose_of(t))
        k = entity_key(t.get("counterparty"))
        t["counterparty_id"] = canon[k] if k else None
        if k:
            rows[canon[k]].append(t)
        else:
            t["relationship"], t["relationship_basis"] = "UNKNOWN", "no identifiable party"

    entities = {}
    for eid, ts in rows.items():
        seen = defaultdict(list)
        for t in ts:
            r = _RELATION_OF.get(t.get("category", ""))
            if r:
                seen[r].append(t)
        rels = set(seen)
        if {"CUSTOMER", "VENDOR"} <= rels:
            rels.add("CUSTOMER & VENDOR")
        relationship = next((r for r in _RANK if r in rels), "UNKNOWN")
        if relationship == "UNKNOWN":
            basis = "no transaction identifies the relationship"
        elif relationship == "CUSTOMER & VENDOR":
            basis = f"pays in ({len(seen['CUSTOMER'])}) and is paid ({len(seen['VENDOR'])})"
        else:
            ev = seen[relationship]
            why = sorted({t.get("subcategory") or t.get("category") for t in ev})
            basis = f"{len(ev)} of {len(ts)} transaction(s): " + "; ".join(why)
        for t in ts:
            t["relationship"], t["relationship_basis"] = relationship, basis
        entities[eid] = {
            "relationship": relationship,
            "basis": basis,
            "names": sorted({t.get("counterparty") for t in ts}),
            "inflow": round(sum(float(t.get("credit") or 0) for t in ts), 2),
            "outflow": round(sum(float(t.get("debit") or 0) for t in ts), 2),
            "count": len(ts),
            # purposes differ by transaction; the relationship does not
            "purposes": _purposes(ts),
        }
    return entities


# '<account>-<channel>-<remark> <id>' (HDFC '50200013789806-TPT-HIRING 0000000241988450'):
# the remark is what the holder said the payment was for
_REMARK_RX = re.compile(rf"^\s*{_ACCT_TOKEN}\s*-\s*(?:[A-Z]{{2,4}}\s*-\s*)?([A-Z][A-Z .&/]*?[A-Z])\s*(?:\d{{6,}}.*)?$", re.I)


def purpose_of(t: dict) -> str:
    """Why this transaction happened, independent of who it was with."""
    m = _REMARK_RX.match(t.get("narration") or "")
    if m:
        return f"{m.group(1).strip().title()} (holder's remark)"
    return t.get("subcategory") or t.get("category") or "-"


def _purposes(ts: list[dict]) -> list[dict]:
    out = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for t in ts:
        p = out[t["purpose"]]
        p["amount"] += float(t.get("credit") or t.get("debit") or 0)
        p["count"] += 1
    return [{"purpose": k, "amount": round(v["amount"], 2), "count": v["count"]}
            for k, v in sorted(out.items(), key=lambda x: -x[1]["amount"])]
