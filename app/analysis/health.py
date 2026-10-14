"""Module 1: Account Health & Facility Analysis.

Computes Average Bank Balance (ABB/AMB), minimum/maximum balances, volatility,
detects account facility (Savings, Current, Overdraft/Cash Credit),
and evaluates OD/CC limit utilization and credit turnover.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import math
import re
from typing import Any

from .account_type import resolve_account_type

# account_type.py's names → the facility names used across the analysis
_FACILITY_OF = {"OD_CC": "OVERDRAFT_CC", "CURRENT": "CURRENT", "SAVINGS": "SAVINGS", "UNKNOWN": "UNKNOWN"}


# Account-type wording and codes seen in statement headers, matched on whole
# words ('CC' must not match inside 'ACCOUNT').
_OD_TYPE_RX = re.compile(
    r"\b(?:OD|CC|OVERDRAFT|CASH\s*CREDIT|HYPOTH\w*|HYGEN|SOD|DROPLINE|KCC)\b", re.I)
_SAVINGS_TYPE_RX = re.compile(r"\b(?:SAVINGS?|SB|SBA|SAV)\b|^SB[\s\-]", re.I)
_CURRENT_TYPE_RX = re.compile(r"\b(?:CURRENT|CA|CAGEN)\b|^CA[\s\-]", re.I)


def facility_from_header(acct_type: str) -> str | None:
    """SAVINGS / CURRENT / OVERDRAFT_CC from the header's account type, or None."""
    t = acct_type or ""
    if _OD_TYPE_RX.search(t):
        return "OVERDRAFT_CC"
    if _SAVINGS_TYPE_RX.search(t):
        return "SAVINGS"
    if _CURRENT_TYPE_RX.search(t):
        return "CURRENT"
    return None


def _printed_limit(info: dict) -> float | None:
    """OD/CC limit printed in the header. 0.00 means no limit, not unknown."""
    v = info.get("od_limit")
    try:
        v = float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError:
        v = None
    return v if v and v > 0 else None


def analyze_account_health(txns: list[dict], info: dict | None = None) -> dict[str, Any]:
    info = info or {}
    if not txns:
        acct = resolve_account_type(info, [], 0, 0)
        return {
            **acct,
            "facility_type": _FACILITY_OF[acct["account_type"]],
            "is_overdraft_facility": False,
            "abb": 0.0,
            "min_balance": 0.0,
            "max_balance": 0.0,
            "closing_balance": 0.0,
            "balance_volatility_std": 0.0,
            "balance_volatility_cv": 0.0,
            "negative_balance_days": 0,
            "zero_balance_days": 0,
            "total_days": 0,
            "estimated_sanctioned_limit": 0.0,
            "average_limit_utilization_pct": 0.0,
            "peak_limit_utilization_pct": 0.0,
            "credit_turnover_to_limit": 0.0,
            "monthly_health": [],
        }

    dated = [t for t in txns if t.get("txn_date") and t.get("balance") is not None]
    if not dated:
        bals = [float(t["balance"]) for t in txns if t.get("balance") is not None]
        mean_b = sum(bals) / len(bals) if bals else 0.0
        neg_cnt = sum(1 for b in bals if b < 0)
        acct = resolve_account_type(info, txns, neg_cnt, len(bals))
        is_od = acct["account_type"] == "OD_CC"
        return {
            **acct,
            "facility_type": _FACILITY_OF[acct["account_type"]],
            "is_overdraft_facility": is_od,
            "abb": round(mean_b, 2),
            "min_balance": round(min(bals), 2) if bals else 0.0,
            "max_balance": round(max(bals), 2) if bals else 0.0,
            "closing_balance": round(bals[-1], 2) if bals else 0.0,
            "balance_volatility_std": 0.0,
            "balance_volatility_cv": 0.0,
            "negative_balance_days": neg_cnt,
            "zero_balance_days": sum(1 for b in bals if b == 0),
            "total_days": len(txns),
            "estimated_sanctioned_limit": 0.0,
            "average_limit_utilization_pct": 0.0,
            "peak_limit_utilization_pct": 0.0,
            "credit_turnover_to_limit": 0.0,
            "monthly_health": [],
        }

    dated.sort(key=lambda t: t["txn_date"])
    start_date: date = dated[0]["txn_date"]
    end_date: date = dated[-1]["txn_date"]

    if info.get("period_from") and hasattr(info["period_from"], "year"):
        start_date = min(start_date, info["period_from"])
    elif info.get("opening_balance_date") and hasattr(info["opening_balance_date"], "year"):
        # no printed period: coverage starts at the balance-forward line, as the
        # month count does (_months_covered); that day holds the opening balance
        start_date = min(start_date, info["opening_balance_date"])
    if info.get("period_to") and hasattr(info["period_to"], "year"):
        end_date = max(end_date, info["period_to"])

    day_last_bal: dict[date, float] = {}
    for t in dated:
        d = t["txn_date"]
        day_last_bal[d] = float(t["balance"])

    daily_balances: list[tuple[date, float]] = []
    curr_date = start_date
    prev_bal = float(dated[0]["balance"])
    if txns[0].get("balance") is not None:
        first_bal = txns[0]["balance"]
        deb = txns[0].get("debit") or Decimal(0)
        crd = txns[0].get("credit") or Decimal(0)
        prev_bal = float(first_bal + deb - crd)

    neg_days = 0
    zero_days = 0
    month_groups: dict[str, list[float]] = defaultdict(list)

    while curr_date <= end_date:
        if curr_date in day_last_bal:
            prev_bal = day_last_bal[curr_date]
        daily_balances.append((curr_date, prev_bal))
        if prev_bal < 0:
            neg_days += 1
        elif prev_bal == 0:
            zero_days += 1

        m_key = curr_date.strftime("%Y-%m")
        month_groups[m_key].append(prev_bal)
        curr_date += timedelta(days=1)

    total_days = len(daily_balances)
    b_values = [b for _, b in daily_balances]
    abb = sum(b_values) / total_days if total_days else 0.0
    min_bal = min(b_values) if b_values else 0.0
    max_bal = max(b_values) if b_values else 0.0
    closing_bal = b_values[-1] if b_values else 0.0

    # Account type from evidence, strongest first (account_type.py): printed
    # type, product code, limit / interest lines, balance pattern, and only
    # then the holder's name — each answer says which step gave it
    acct = resolve_account_type(info, txns, neg_days, total_days)
    facility_type = _FACILITY_OF[acct["account_type"]]
    facility_source = f"step {acct['account_type_step']} ({acct['account_type_confidence']}): " \
                      f"{acct['account_type_evidence']}"
    is_od = facility_type == "OVERDRAFT_CC"

    # OD / CC limit analytics only against a limit the statement prints;
    # peak overdraft rounded up to a slab is a guess, not a sanction.
    printed_limit = _printed_limit(info)
    est_limit = printed_limit or 0.0
    avg_util_pct = None
    peak_util_pct = None
    turnover_to_limit = None

    total_credits = sum(float(t["credit"]) for t in txns if t.get("credit"))

    if is_od and printed_limit and min_bal < 0:
        neg_bals = [abs(b) for b in b_values if b < 0]
        avg_neg = sum(neg_bals) / len(neg_bals) if neg_bals else 0.0
        avg_util_pct = (avg_neg / est_limit * 100) if est_limit > 0 else 0.0
        peak_util_pct = (abs(min_bal) / est_limit * 100) if est_limit > 0 else 0.0

        # Annualized turnover multiplier
        months_span = max(1.0, total_days / 30.0)
        annualized_credits = (total_credits / months_span) * 12.0
        turnover_to_limit = annualized_credits / est_limit if est_limit > 0 else 0.0

    # Volatility
    variance = sum((x - abb) ** 2 for x in b_values) / total_days if total_days > 1 else 0.0
    std_dev = math.sqrt(variance)
    cv = (std_dev / abs(abb)) if abs(abb) > 0.01 else 0.0

    monthly_health = []
    for m_key in sorted(month_groups.keys()):
        m_bals = month_groups[m_key]
        m_abb = sum(m_bals) / len(m_bals) if m_bals else 0.0
        m_min = min(m_bals) if m_bals else 0.0
        m_max = max(m_bals) if m_bals else 0.0
        m_close = m_bals[-1] if m_bals else 0.0
        m_neg = sum(1 for x in m_bals if x < 0)
        monthly_health.append({
            "month": m_key,
            "abb": round(m_abb, 2),
            "min_balance": round(m_min, 2),
            "max_balance": round(m_max, 2),
            "closing_balance": round(m_close, 2),
            "negative_days": m_neg,
            "days_in_month": len(m_bals),
        })

    return {
        "facility_type": facility_type,
        "facility_type_source": facility_source,
        **acct,
        "od_limit_source": "PRINTED" if printed_limit else "NOT PRINTED (utilisation not scored)",
        "is_overdraft_facility": is_od,
        "abb": round(abb, 2),
        "min_balance": round(min_bal, 2),
        "max_balance": round(max_bal, 2),
        "closing_balance": round(closing_bal, 2),
        "balance_volatility_std": round(std_dev, 2),
        "balance_volatility_cv": round(cv, 4),
        "negative_balance_days": neg_days,
        "zero_balance_days": zero_days,
        "total_days": total_days,
        "estimated_sanctioned_limit": round(est_limit, 2) if est_limit else None,
        "average_limit_utilization_pct": round(avg_util_pct, 2) if avg_util_pct is not None else None,
        "peak_limit_utilization_pct": round(peak_util_pct, 2) if peak_util_pct is not None else None,
        "credit_turnover_to_limit": round(turnover_to_limit, 2) if turnover_to_limit is not None else None,
        "monthly_health": monthly_health,
    }
