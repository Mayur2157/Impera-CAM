"""The CAM as JSON for the portal and the public API (api-contract.md → CamResult).

Written beside the workbook and purged with it. Only what the contract names
is kept: the account number is masked here, and the holder's email, phone,
address and PAN are never written, so the file carries no more personal data
than the screen shows. Narrations stay verbatim except for the holder's own
account number, which some banks print in them (HDFC).
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from decimal import Decimal

# points each scorecard component can earn (profiler.py weights)
MAX_POINTS = {
    "cashflow_margin_score": 20, "liquidity_abb_score": 15, "debt_capacity_score": 15,
    "emi_regularity_score": 10, "facility_compliance_score": 15, "bounce_behavior_score": 10,
    "transaction_risk_score": 10, "income_concentration_score": 5,
}

_METRICS = (
    "abb", "monthly_eligible_income", "net_cash_flow", "total_monthly_emi",
    "total_monthly_debt_service", "foir_percentage", "dscr", "dscr_display",
    "outward_bounces", "loan_emi_bounces_count", "cash_share_of_inflows_pct",
    "average_limit_utilization_pct", "gross_bank_inflows", "gross_debits",
    "income_metric_label", "debt_ratio_label",
)


def mask_account(number) -> str | None:
    """Keep the last four characters: 50100012345678 → XXXXXXXXXX5678."""
    s = "".join(str(number or "").split())
    if not s or s.upper() == "N/A":
        return None
    keep = 4 if len(s) > 4 else max(len(s) - 2, 0)
    return "X" * (len(s) - keep) + s[len(s) - keep:]


def _scrubber(number):
    """Masks the holder's own account number where the bank prints it in a narration."""
    own = "".join(str(number or "").split())
    masked = mask_account(own)
    if len(own) <= 4 or not masked:
        return lambda text: text
    return lambda text: text.replace(own, masked) if text else text


def _num(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def _day(v) -> str | None:
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    return v or None


def _monthly(profile: dict) -> list[dict]:
    health = {m["month"]: m for m in (profile.get("account_health") or {}).get("monthly_health") or []}
    out = []
    for m in (profile.get("cash_flow") or {}).get("monthly_summary") or []:
        h = health.get(m["month"], {})
        out.append({"month": m["month"], "inflow": m.get("inflow"), "outflow": m.get("outflow"),
                    "net": m.get("net_flow"), "closing_balance": h.get("closing_balance"),
                    "abb": h.get("abb")})
    return out


def _income(profile: dict) -> dict:
    inc = profile.get("eligible_income") or {}
    months = inc.get("months_count") or 1
    return {
        "eligible": [{"category": c["category"], "count": c.get("count", 0), "amount": c.get("amount", 0),
                      "monthly": round((c.get("amount") or 0) / months, 2)}
                     for c in inc.get("eligible_categories") or [] if c.get("count")],
        "excluded": [{"category": c["category"], "count": c.get("count", 0), "amount": c.get("amount", 0),
                      "reason": c.get("reason")}
                     for c in inc.get("excluded_categories") or [] if c.get("count")],
    }


def _parties(rows) -> list[dict]:
    return [{"name": p.get("counterparty"), "count": p.get("count"), "total": p.get("total_amount"),
             "share_pct": p.get("share_pct")} for p in rows or []]


def build(profile: dict, issues: list, strategy: str | None, mode: str | None) -> dict:
    """CamResult without `file` (the API adds that from the job row)."""
    es = profile.get("executive_summary") or {}
    debt = profile.get("debt_analysis") or {}
    risk = profile.get("risk_analysis") or {}
    aml = profile.get("fraud_aml") or {}
    parties = profile.get("counterparties") or {}
    validation = profile.get("statement_validation") or {}
    scrub = _scrubber(es.get("account_number"))
    flagged: dict[int, str] = {}         # row index → first issue found on it
    for i, why in issues:
        flagged.setdefault(i, why)

    txns = []
    for n, t in enumerate(profile.get("annotated_transactions") or [], 1):
        txns.append({
            "sno": n, "date": _day(t.get("txn_date")), "value_date": _day(t.get("value_date")),
            "narration": scrub(t.get("narration")),
            "reference": str(t["reference"]) if t.get("reference") is not None else None,
            "debit": _num(t.get("debit")), "credit": _num(t.get("credit")),
            "balance": _num(t.get("balance")),
            "category": t.get("category") or "GENERAL_TRANSFER",
            "counterparty": t.get("counterparty") or "Unknown",
            "status": "CHECK" if (n - 1) in flagged else "OK", "page": t.get("page", 1),
        })

    return {
        "account": {
            "account_holder": es.get("account_holder"),
            "bank_name": es.get("bank_name"),
            "account_number_masked": mask_account(es.get("account_number")),
            "facility_type": es.get("facility_type"),
            "account_type": es.get("account_type"),
            "customer_persona": es.get("customer_persona"),
            "analysis_period": es.get("analysis_period"),
            "months_count": es.get("months_count"),
            "data_sufficiency": es.get("data_sufficiency"),
        },
        "score": {
            "credit_score_index": es.get("credit_score_index"),
            "risk_rating": es.get("risk_rating"),
            "score_before_caps": es.get("score_before_caps"),
            "scorecard_breakdown": {k: (es.get("scorecard_breakdown") or {}).get(k) for k in MAX_POINTS},
            "max_points": dict(MAX_POINTS),
            "hard_cap_rules_applied": es.get("hard_cap_rules_applied") or [],
            "strengths": es.get("strengths") or [],
            "red_flags": es.get("red_flags") or [],
            "unscored_reasons": es.get("unscored_reasons") or {},
        },
        "metrics": {k: es.get(k) for k in _METRICS},
        "monthly": _monthly(profile),
        "income": _income(profile),
        "debt": {"loans": [{
            "lender": ln.get("lender"), "monthly_emi": ln.get("typical_emi_amount"),
            "installments": ln.get("installments_detected"), "total_paid": ln.get("total_paid"),
            "last_paid": ln.get("last_paid_date"), "status": ln.get("status"),
            "linked_bounces": ln.get("linked_bounces", 0),
        } for ln in debt.get("loans") or []]},
        "counterparties": {"top_inward": _parties(parties.get("top_inward_parties")),
                           "top_outward": _parties(parties.get("top_outward_parties"))},
        "risk": {
            "bounces": [{"date": b.get("date"), "type": b.get("type"), "amount": b.get("bounce_amount"),
                         "narration": scrub(b.get("narration"))} for b in risk.get("bounces") or []],
            "structuring": [{"date": s.get("date"), "amount": s.get("amount"),
                             "confidence": s.get("confidence_level")}
                            for s in aml.get("structuring_alerts") or []],
            "rapid_in_out": [{"credit_date": c.get("credit_date"), "debit_date": c.get("debit_date"),
                              "amount": c.get("credit_amount"), "confidence": c.get("confidence_level")}
                             for c in risk.get("rapid_in_out_cycles") or []],
        },
        "validation": {
            "strategy": strategy, "chain_mode": mode,
            "pass_rate": validation.get("balance_chain_pass_rate_pct"),
            "flagged_rows": [{"row": i + 1, "issue": why} for i, why in sorted(flagged.items())],
        },
        "transactions": txns,
    }


def _encode(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    raise TypeError(f"{type(v).__name__} is not JSON serialisable")


def write(path: str, cam: dict) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cam, fh, ensure_ascii=False, default=_encode)
    return path


def read(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
