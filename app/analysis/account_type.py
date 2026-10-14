"""What kind of account a statement is for, and who holds it.

Two separate questions:

- Account type (OD_CC / CURRENT / SAVINGS / UNKNOWN) decides whether the
  facility and limit components are scored. It is resolved from evidence,
  strongest first, and every step says where its answer came from:
    1. printed type: a labelled header field or the statement title (HIGH)
    2. product code: a labelled code with a CA / SB / SA / CC / OD prefix (HIGH)
    3. facility and interest lines for this account (MEDIUM-HIGH to HIGH):
       a printed limit above zero or monthly debit interest → OD_CC;
       savings interest credited → SAVINGS (current accounts earn none)
    4. balance behaviour (MEDIUM): negative on most days → OD_CC; never
       negative → NOT_OD only (it cannot tell current from savings)
    5. holder name (LOW): only when 1-4 leave NOT_OD
    6. otherwise UNKNOWN
  Evidence that disagrees with the answer is kept as a conflict.

- Borrower type (BUSINESS / INDIVIDUAL / UNKNOWN) decides DSCR vs FOIR and
  the persona. Here an entity name ('… PRIVATE LIMITED') is strong evidence.
"""
from __future__ import annotations

import re

_CONF_RANK = {"HIGH": 3, "MEDIUM_HIGH": 2, "MEDIUM": 1, "LOW": 0, "NONE": -1}

# Step 1: words of a printed type → a type. Whole words, so 'HYPOTHICATION CASH
# CREDIT' (JPCB's spelling) still reads as cash credit, and 'CC' never matches
# inside 'ACCOUNT'.
_OD_WORDS = re.compile(r"\b(?:CASH\s*CREDIT|OVER\s*DRAFT|OD|CC|SOD|HYPOTH\w*|DROPLINE|KCC)\b", re.I)
_CURRENT_WORDS = re.compile(r"\bCURRENT\b|^\s*CA\b|^\s*CA[\s\-]", re.I)
_SAVINGS_WORDS = re.compile(r"\bSAVINGS?\b|^\s*SB\b|^\s*SA[\s\-]|\bSB\s", re.I)

# Step 2: a labelled product code's prefix
_CODE_PREFIX = [(re.compile(r"^(?:CC|OD)[\s\-]", re.I), "OD_CC"),
                (re.compile(r"^CA[\s\-]", re.I), "CURRENT"),
                (re.compile(r"^S[BA][\s\-]?", re.I), "SAVINGS")]

# Step 3: interest lines ('02154400000010:Int.Coll:01-04-2023 to 30-04-2023',
# 'SBINT FOR THE PERIOD …', 'Saving: Int.Pd:…', 'CREDIT OF INTEREST')
_DEBIT_INTEREST_RX = re.compile(r"\bINT\.?\s*COLL|\bINTEREST\s*(?:COLLECTED|DEBITED|CHARGED|COLL)\b|\bDR\.?\s*INT\b", re.I)
# 'INT' must be the word or its abbreviation, close to 'SAVING': 'NEFT FROM
# SAVINGS A/C INTERNET BANKING' is a transfer, not interest
_CREDIT_INTEREST_RX = re.compile(
    r"\bSB\s*INT(?:EREST|\.|\b)|\bSBINT\b|\bSAVINGS?\b[\s:.\-]{0,4}(?:BANK\s+)?INT(?:EREST|\.|\b)|"
    r"\bINT\.?\s*PD\b|\bCREDIT\s*(?:OF\s*)?INTEREST\b|\bINTEREST\s*(?:CREDIT(?:ED)?|CAPITALI[SZ]ED|PAID)\b", re.I)
# interest on a deposit swept in is not savings interest
_DEPOSIT_RX = re.compile(r"\b(?:FD|TDR?|RD|FIXED|TERM\s*DEPOSIT|RECURRING)\b", re.I)

_ENTITY_RX = re.compile(
    r"\b(?:LTD|LIMITED|PVT|PRIVATE|LLP|ENTERPRISES?|TRADERS|TRADING|CORPORATION|CORP|INDUSTRIES|"
    r"INTERNATIONAL|AGENC(?:Y|IES)|SALES|SERVICES|SOLUTIONS|ELECTRONICS|ELECTRICALS|ENGINEERING|"
    r"MOVERS|VENTURES|CONNECTION|STORES|FIRM|ASSOCIATES|EXPORTS?|IMPORTS?|CO|COMPANY|HUF)\b", re.I)


def is_entity_name(name: str) -> bool:
    """A firm's name ('HEENA CARGO MOVERS PRIVATE LIMITED', 'K P ENTERPRISES')."""
    return bool(_ENTITY_RX.search(name or ""))


def _type_from_words(text: str) -> str | None:
    t = text or ""
    if _OD_WORDS.search(t):
        return "OD_CC"
    if _CURRENT_WORDS.search(t):
        return "CURRENT"
    if _SAVINGS_WORDS.search(t):
        return "SAVINGS"
    return None


def _subtype(raw: str) -> str | None:
    t = (raw or "").upper()
    if re.search(r"CASH\s*CREDIT", t):
        return "CASH_CREDIT"
    if re.search(r"OVER\s*DRAFT|\bOD\b|\bSOD\b", t):
        return "OVERDRAFT"
    return None


def _limit(info: dict) -> float | None:
    v = info.get("od_limit")
    try:
        return float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError:
        return None


def _own(narration: str, account: str) -> bool:
    """An interest line refers to this account: it names no account, or this
    one (in full or as its masked tail). 'OD- 12165010107' is another account."""
    nums = re.findall(r"\d{9,18}", narration or "")
    if not nums:
        return True
    tail = account[-4:] if account else ""
    return any(n == account or (tail and n.endswith(tail)) for n in nums)


def resolve_account_type(info: dict, txns: list[dict], negative_days: int, total_days: int) -> dict:
    account = re.sub(r"\D", "", str(info.get("account_number") or ""))
    raw = (info.get("account_type") or "").strip() or None
    ev: list[tuple[str, int, str, str]] = []          # (type, step, confidence, evidence)

    # 1. printed type (labelled field / title only; never free text)
    if raw:
        t = _type_from_words(raw)
        if t:
            ev.append((t, 1, "HIGH", f"printed account type: {raw}"))
    # 2. labelled product code
    code = (info.get("product_code") or "").strip()
    if code:
        t = next((ty for rx, ty in _CODE_PREFIX if rx.search(code)), None)
        if t:
            ev.append((t, 2, "HIGH", f"product code: {code}"))
    # 3. facility and interest evidence for this account
    limit = _limit(info)
    if limit and limit > 0:
        ev.append(("OD_CC", 3, "HIGH", f"printed limit {limit:,.2f}"))
    dr_int = [t for t in txns if t.get("debit") and _DEBIT_INTEREST_RX.search(t.get("narration") or "")
              and _own(t.get("narration"), account)]
    if dr_int:
        ev.append(("OD_CC", 3, "HIGH", f"{len(dr_int)} debit-interest {'entry' if len(dr_int) == 1 else 'entries'}: {dr_int[0]['narration'][:60]}"))
    cr_int = [t for t in txns if t.get("credit") and _CREDIT_INTEREST_RX.search(t.get("narration") or "")
              and not _DEPOSIT_RX.search(t.get("narration") or "") and _own(t.get("narration"), account)]
    if cr_int:
        ev.append(("SAVINGS", 3, "MEDIUM_HIGH",
                   f"{len(cr_int)} savings-interest credit(s): {cr_int[0]['narration'][:60]}"))
    # 4. balance behaviour: tells OD from not-OD only
    neg_share = negative_days / total_days if total_days else 0.0
    if neg_share >= 0.5:
        ev.append(("OD_CC", 4, "MEDIUM", f"negative end-of-day balance on {neg_share:.0%} of days"))
    not_od = (limit == 0.0) or (total_days > 0 and negative_days == 0)

    warnings = []
    if 0 < neg_share < 0.5 and not dr_int:
        warnings.append(f"negative balance on {negative_days} of {total_days} days with no debit interest: "
                        f"possible temporary overdraft on a deposit account")

    best = max(ev, key=lambda e: (_CONF_RANK[e[2]], -e[1]), default=None)
    if best is None and not_od:
        # 5. holder name, only when the evidence says 'not OD' and nothing more
        name = info.get("customer_name") or ""
        if name:
            t = "CURRENT" if is_entity_name(name) else "SAVINGS"
            why = "limit printed as 0.00" if limit == 0.0 else "balance never negative"
            best = (t, 5, "LOW", f"holder name only ({'firm' if t == 'CURRENT' else 'personal'} name); "
                                 f"{why} shows NOT_OD")
    if best is None:
        best = ("UNKNOWN", 6, "NONE", "no printed type, code, limit, interest line or decisive balance pattern")

    conflicts = [f"{e[0]} ({e[3]})" for e in ev
                 if e[0] != best[0] and _CONF_RANK[e[2]] >= _CONF_RANK["MEDIUM"]]
    if best[0] == "SAVINGS" and neg_share >= 0.5:
        conflicts.append(f"savings account negative on {neg_share:.0%} of days")
    return {
        "account_type": best[0],
        "account_subtype": _subtype(raw) if best[0] == "OD_CC" else None,
        "account_type_raw": raw,
        "account_type_step": best[1],
        "account_type_confidence": best[2],
        "account_type_evidence": best[3],
        "account_type_conflicts": conflicts,
        "account_type_warnings": warnings,
    }


def resolve_borrower_type(info: dict, account_type: str, account_conf: str) -> dict:
    """BUSINESS / INDIVIDUAL / UNKNOWN, for DSCR vs FOIR and the persona."""
    name = info.get("customer_name") or ""
    if name and is_entity_name(name):
        return {"borrower_type": "BUSINESS", "borrower_type_confidence": "HIGH",
                "borrower_type_evidence": f"firm name: {name}"}
    strong = _CONF_RANK.get(account_conf, -1) >= _CONF_RANK["MEDIUM"]
    if account_type in ("CURRENT", "OD_CC") and strong:
        return {"borrower_type": "BUSINESS", "borrower_type_confidence": "MEDIUM",
                "borrower_type_evidence": f"{account_type} account ({account_conf.lower()} confidence)"
                                          + ("; personal name — possibly a proprietor" if name else "")}
    if name:
        return {"borrower_type": "INDIVIDUAL", "borrower_type_confidence": "HIGH" if account_type == "SAVINGS" else "MEDIUM",
                "borrower_type_evidence": f"personal name: {name}"}
    if account_type == "SAVINGS" and strong:
        return {"borrower_type": "INDIVIDUAL", "borrower_type_confidence": "LOW",
                "borrower_type_evidence": "savings account; holder name not found"}
    return {"borrower_type": "UNKNOWN", "borrower_type_confidence": "NONE",
            "borrower_type_evidence": "holder name not found and account type not decisive"}
