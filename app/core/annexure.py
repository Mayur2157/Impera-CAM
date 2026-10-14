"""Party-detail annexures printed after the transaction table.

Some banks (JPCB) print the payer/payee of each NEFT/RTGS/IMPS only in a
separate 'INWARD / OUTWARD DETAILS' table; the main row just says
'Cr Cust Account'. This reads that table and joins it back to the rows by
date, amount and direction so the analysis can name the party.
"""
import re
from decimal import Decimal

from .normalize import parse_date

_HEAD_RX = re.compile(r"(?:IMPS|NEFT|RTGS)[\s/]+.*(?:INWARD|OUTWARD).*DETAILS", re.I)
# '11/04/2023 I RTGS 0.00 539000.00'
_ENTRY_RX = re.compile(
    r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+([IO])\s+(NEFT|RTGS|IMPS)\b.*?([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$",
    re.I)
_GENERIC_NAME_RX = re.compile(r"PAYLINK|\bACCOUNT\b|\bA/C\b|^\s*$", re.I)


def _fields(line):
    return [f.strip() for f in line.split(",")]


def _party(detail_lines):
    """Name and account from 'IFSC-…,ACNO-…,<NAME>,UTR-…' plus the line after it."""
    name, acct = None, None
    if detail_lines:
        for f in _fields(detail_lines[0]):
            m = re.match(r"ACNO-\s*(\d*)", f, re.I)
            if m:
                acct = m.group(1) or None
                continue
            if re.match(r"(?:IFSC|UTR)-", f, re.I) or not re.search(r"[A-Za-z]{3}", f):
                continue
            name = f
            break
    if (not name or _GENERIC_NAME_RX.search(name)) and len(detail_lines) > 1:
        first = _fields(detail_lines[1])[0]
        if re.search(r"[A-Za-z]{3}", first):
            # the account on the first line was the pool's ('CSF PAYLINK ACCOUNT'), not this party's
            if name:
                acct = None
            name = first
    return (name.strip() if name else None), acct


def parse_party_annexure(pdf):
    entries = []
    for page in pdf.pages:
        text = page.extract_text() or ""
        if not _HEAD_RX.search(text):
            continue
        lines = text.splitlines()
        start = next(i for i, ln in enumerate(lines) if _HEAD_RX.search(ln))
        cur = None
        for ln in lines[start + 1:]:
            m = _ENTRY_RX.match(ln.strip())
            if m:
                if cur:
                    entries.append(cur)
                dr = Decimal(m.group(4).replace(",", ""))
                cr = Decimal(m.group(5).replace(",", ""))
                cur = {"date": parse_date(m.group(1)), "direction": "O" if dr > 0 else "I",
                       "amount": dr if dr > 0 else cr, "channel": m.group(3).upper(), "lines": []}
            elif cur is not None and ln.strip() and not re.match(r"^(?:TOTAL|BR\s*MANAGER)", ln.strip(), re.I):
                cur["lines"].append(ln.strip())
        if cur:
            entries.append(cur)
    for e in entries:
        utr = next((m.group(1) for ln in e["lines"] for m in [re.search(r"UTR-\s*([A-Z0-9]{8,})", ln, re.I)] if m), None)
        e["utr"] = utr
        e["name"], e["account"] = _party(e.pop("lines"))
    return [e for e in entries if e["date"] and e["name"]]


def attach_party_hints(txns, entries):
    """Give each matching row 'party_hint' / 'party_account' from the annexure."""
    used = set()
    for t in txns:
        amt = t.get("debit") or t.get("credit")
        if not amt:
            continue
        direction = "O" if t.get("debit") else "I"
        for i, e in enumerate(entries):
            if i in used or e["direction"] != direction or e["amount"] != amt:
                continue
            if t.get("txn_date") and abs((t["txn_date"] - e["date"]).days) > 1:
                continue
            t["party_hint"] = e["name"]
            if e["account"]:
                t["party_account"] = e["account"]
            # the row prints no reference ('Cr Cust Account'); the annexure
            # carries the transfer's UTR, so that is its reference
            if e.get("utr") and not (t.get("reference") or "").strip():
                t["reference"] = e["utr"]
                t["reference_source"] = "annexure"
            used.add(i)
            break
    return txns
