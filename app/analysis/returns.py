"""Cheque and mandate returns, classified by what the money does.

Every bank words returns differently ('O/W RTN', 'IW INST … REJECTED',
'ACH-RT-CHG', 'HRETCHARGE'), but the money moves the same way everywhere.
A charge only counts when its wording says something was returned; a lien
or mandate fee ('LIEN MARKING FOR NACH') is a fee, not evidence of a bounce.

- A cheque the customer DEPOSITED came back (the payer bounced): a debit equal
  to an earlier credit, usually naming the same instrument number.
- The customer's OWN payment bounced: the bank posts only a small return
  charge (₹100-₹750 plus GST) with nothing to reverse, or reverses a mandate
  debit it had posted.

Keywords only confirm that a row is a return; they never decide the side on
their own, and a payee name ('MB:Bounce') is never a return.
"""
from __future__ import annotations

import re

RETURN_KW_RX = re.compile(
    r"\bRTN\b|\bRETURN(?:ED)?\b|\bRET\b|REJECT|DISHONOU?R|UNPAID|INSUFF|\bBOUNCE|HRET|RT-CHG|"
    r"\bACHRE\b|REFER\s*TO\s*DRAWER|SIGNATURE\s*DIFFER", re.I)
# Kotak MB:/IB: and UPI/NEFT/IMPS remarks name a payee; 'MB:Bounce' is a person
_PAYEE_PREFIX_RX = re.compile(r"^(?:MB|IB|UPI|IMPS|NEFT|RTGS)\b\s*[:/\-]", re.I)
# 'O/W' = outward clearing: a cheque the customer sent for collection
_DEPOSIT_SIDE_RX = re.compile(r"^(?:O/?W|OW)\b|OUTWARD\s*RET|RETURN\s*OF\s*.*DEPOSIT", re.I)
# 'I/W' = inward clearing: the customer's own cheque; mandates are always own
_OWN_SIDE_RX = re.compile(r"^(?:I/?W|IW)\b|INWARD\s*RET|\bN?ACH|ECS|MANDATE|HRET", re.I)
_MANDATE_RX = re.compile(r"\bN?ACH|ECS|MANDATE", re.I)
_REVERSAL_RX = re.compile(r"\bRET(?:URN)?\b|\bRTN\b|\bREV(?:ERSAL|D)?\b|REJECT", re.I)

CHARGE_MAX = 900.0          # ₹750 + 18% GST, rounded up
DEPOSIT_WINDOW_DAYS = 10


def _instruments(text):
    return set(re.findall(r"(?<!\d)(\d{3,8})(?!\d)", text or ""))


def _amt(t, key):
    v = t.get(key)
    return float(v) if v else 0.0


def find_returns(txns: list[dict]) -> dict[int, dict]:
    """Map row index → {'side': 'OWN' | 'DEPOSIT' | 'UNRESOLVED', 'is_charge', 'matched'}."""
    out: dict[int, dict] = {}
    for i, t in enumerate(txns):
        narr = (t.get("narration") or "").strip()
        deb, crd = _amt(t, "debit"), _amt(t, "credit")

        # A mandate debit that the bank posted and then reversed
        if crd > 0 and _MANDATE_RX.search(narr) and _REVERSAL_RX.search(narr):
            for j in range(i - 1, -1, -1):
                p = txns[j]
                if p.get("txn_date") and t.get("txn_date") and (t["txn_date"] - p["txn_date"]).days > 3:
                    break
                if abs(_amt(p, "debit") - crd) < 0.5:
                    out[i] = {"side": "OWN", "is_charge": False, "matched": j}
                    out[j] = {"side": "OWN", "is_charge": False, "matched": i, "reversed": True}
                    break
            continue

        if deb <= 0 or not RETURN_KW_RX.search(narr) or _PAYEE_PREFIX_RX.match(narr):
            continue

        inst = _instruments(narr)
        best = None
        for j in range(i - 1, -1, -1):
            p = txns[j]
            if p.get("txn_date") and t.get("txn_date") and \
                    (t["txn_date"] - p["txn_date"]).days > DEPOSIT_WINDOW_DAYS:
                break
            if abs(_amt(p, "credit") - deb) >= 0.5:
                continue
            p_inst = _instruments(f"{p.get('narration') or ''} {p.get('reference') or ''}")
            if inst & p_inst:
                best = j
                break
            if best is None and not inst:
                best = j
        if best is not None:
            out[i] = {"side": "DEPOSIT", "is_charge": False, "matched": best}
        elif _DEPOSIT_SIDE_RX.search(narr):
            out[i] = {"side": "DEPOSIT", "is_charge": False, "matched": None}
        elif deb <= CHARGE_MAX or _OWN_SIDE_RX.search(narr):
            out[i] = {"side": "OWN", "is_charge": deb <= CHARGE_MAX, "matched": None}
        else:
            out[i] = {"side": "UNRESOLVED", "is_charge": False, "matched": None}
    return out
