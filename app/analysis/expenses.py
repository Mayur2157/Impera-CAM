"""Module 3: Expense Analysis.

Categorizes debits into Monthly Expenses, Recurring Payments, Cash Withdrawals,
Utilities, Rent, Insurance, and Statutory/Tax obligations.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .narration_rules import (
    UTILITY_RX,
    RENT_RX,
    INSURANCE_RX,
    TAX_RX,
    extract_counterparty,
)


def analyze_expenses(txns: list[dict]) -> dict[str, Any]:
    debits = [t for t in txns if t.get("debit") and t["debit"] > 0]
    total_debit_val = sum(float(t["debit"]) for t in debits)

    monthly_expenses = defaultdict(float)
    monthly_cash = defaultdict(float)

    cash_txns = []
    utility_txns = []
    rent_txns = []
    insurance_txns = []
    tax_txns = []
    cparty_debits = defaultdict(list)

    import re
    cash_rx = re.compile(r"\b(?:ATM|CASH|CWDR|CDM|EAW|NFS|SELF)\b", re.I)

    # One definition for the whole report: when the classifier has run, its
    # category decides (a 'WRNG CASH … REV' reversal is not a cash withdrawal;
    # a 'billdesk.recharge' UPI is a utility). The patterns below are only a
    # fallback for unclassified input.
    by_cat = {"CASH_WITHDRAWAL": cash_txns, "UTILITY_BILL": utility_txns, "RENT_EXPENSE": rent_txns,
              "INSURANCE_PREMIUM": insurance_txns, "TAX_GST": tax_txns}
    for t in debits:
        amt = float(t["debit"])
        narr = t.get("narration") or ""
        cat = t.get("category")
        if cat is not None:
            bucket = by_cat.get(cat)
        elif cash_rx.search(narr):
            bucket = cash_txns
        elif UTILITY_RX.search(narr):
            bucket = utility_txns
        elif RENT_RX.search(narr):
            bucket = rent_txns
        elif INSURANCE_RX.search(narr):
            bucket = insurance_txns
        elif TAX_RX.search(narr):
            bucket = tax_txns
        else:
            bucket = None
        if bucket is not None:
            bucket.append(t)
        d = t.get("txn_date")
        if d:
            m_key = d.strftime("%Y-%m")
            monthly_expenses[m_key] += amt
            if bucket is cash_txns:
                monthly_cash[m_key] += amt

        cp = t.get("counterparty") or extract_counterparty(narr, t.get("reference") or "")
        cparty_debits[cp].append(amt)

    # Recurring debits (counterparties paid >= 2 times)
    recurring_expenses = []
    for cp, amts in cparty_debits.items():
        if len(amts) >= 2 and cp not in {"Cash", "Atm", "Self", "Unknown"}:
            recurring_expenses.append({
                "counterparty": cp,
                "count": len(amts),
                "total_amount": round(sum(amts), 2),
                "avg_amount": round(sum(amts) / len(amts), 2),
            })
    recurring_expenses.sort(key=lambda x: x["total_amount"], reverse=True)

    total_cash = sum(float(t["debit"]) for t in cash_txns)
    total_utility = sum(float(t["debit"]) for t in utility_txns)
    total_rent = sum(float(t["debit"]) for t in rent_txns)
    total_insurance = sum(float(t["debit"]) for t in insurance_txns)
    total_tax = sum(float(t["debit"]) for t in tax_txns)

    cash_pct = (total_cash / total_debit_val * 100) if total_debit_val > 0 else 0.0

    sorted_months = sorted(monthly_expenses.keys())
    m_breakdown = [
        {
            "month": m,
            "total_expenses": round(monthly_expenses[m], 2),
            "cash_withdrawals": round(monthly_cash[m], 2),
        }
        for m in sorted_months
    ]

    return {
        "total_debits": round(total_debit_val, 2),
        "total_cash_withdrawals": round(total_cash, 2),
        "cash_withdrawal_count": len(cash_txns),
        "cash_to_debit_ratio": round(cash_pct, 2),
        "utility_expenses": round(total_utility, 2),
        "utility_count": len(utility_txns),
        "rent_expenses": round(total_rent, 2),
        "rent_count": len(rent_txns),
        "insurance_expenses": round(total_insurance, 2),
        "insurance_count": len(insurance_txns),
        "tax_expenses": round(total_tax, 2),
        "tax_count": len(tax_txns),
        "top_recurring_expenses": recurring_expenses[:8],
        "monthly_breakdown": m_breakdown,
    }
