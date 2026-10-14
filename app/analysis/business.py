"""Module 11: Business & Commercial Analysis.

Evaluates revenue/expense trends, customer/vendor concentration risks,
and seasonal revenue swings for commercial entity assessment.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def analyze_business(
    txns: list[dict],
    inward_parties: list[dict],
    outward_parties: list[dict],
    monthly_operating: list[dict] | None = None,
) -> dict[str, Any]:
    monthly_rev = defaultdict(float)
    monthly_exp = defaultdict(float)

    total_credits = 0.0
    total_debits = 0.0

    for t in txns:
        c = float(t["credit"]) if t.get("credit") else 0.0
        d = float(t["debit"]) if t.get("debit") else 0.0
        total_credits += c
        total_debits += d
        dt = t.get("txn_date")
        if dt:
            m_key = dt.strftime("%Y-%m")
            monthly_rev[m_key] += c
            monthly_exp[m_key] += d

    # Revenue is the same eligible-receipts figure the rest of the report uses,
    # not gross credits (own transfers and loans are not revenue)
    if monthly_operating:
        monthly_rev = defaultdict(float, {m["month"]: m["eligible_receipts"] for m in monthly_operating})
        monthly_exp = defaultdict(float, {m["month"]: m["operating_expenses"] + m["debt_service"] for m in monthly_operating})

    sorted_months = sorted(set(monthly_rev.keys()) | set(monthly_exp.keys()))
    monthly_trends = []
    prev_rev = None

    for m in sorted_months:
        rev = monthly_rev[m]
        exp = monthly_exp[m]
        growth = ((rev - prev_rev) / prev_rev * 100) if (prev_rev and prev_rev > 0) else 0.0
        monthly_trends.append({
            "month": m,
            "revenue": round(rev, 2),
            "expenses": round(exp, 2),
            "mom_growth_pct": round(growth, 2),
        })
        prev_rev = rev

    # Seasonality
    rev_values = [x["revenue"] for x in monthly_trends if x["revenue"] > 0]
    if rev_values:
        peak_rev = max(rev_values)
        trough_rev = min(rev_values)
        avg_rev = sum(rev_values) / len(rev_values)
        peak_month = next(x["month"] for x in monthly_trends if x["revenue"] == peak_rev)
        trough_month = next(x["month"] for x in monthly_trends if x["revenue"] == trough_rev)
        seasonality_index = peak_rev / avg_rev if avg_rev > 0 else 1.0
    else:
        peak_month = trough_month = "-"
        peak_rev = trough_rev = avg_rev = 0.0
        seasonality_index = 1.0

    # Concentration
    top1_cust_pct = inward_parties[0]["share_pct"] if inward_parties else 0.0
    top3_cust_pct = sum(x["share_pct"] for x in inward_parties[:3])
    top5_cust_pct = sum(x["share_pct"] for x in inward_parties[:5])

    top1_vend_pct = outward_parties[0]["share_pct"] if outward_parties else 0.0
    top3_vend_pct = sum(x["share_pct"] for x in outward_parties[:3])
    top5_vend_pct = sum(x["share_pct"] for x in outward_parties[:5])

    cust_risk = "HIGH CONCENTRATION" if top3_cust_pct > 60 else ("MODERATE" if top3_cust_pct > 35 else "DIVERSIFIED")
    vend_risk = "HIGH CONCENTRATION" if top3_vend_pct > 60 else ("MODERATE" if top3_vend_pct > 35 else "DIVERSIFIED")

    return {
        "monthly_trends": monthly_trends,
        "peak_revenue_month": peak_month,
        "peak_revenue_amount": round(peak_rev, 2),
        "trough_revenue_month": trough_month,
        "trough_revenue_amount": round(trough_rev, 2),
        "seasonality_index": round(seasonality_index, 2),
        "customer_concentration": {
            "top1_share_pct": round(top1_cust_pct, 2),
            "top3_share_pct": round(top3_cust_pct, 2),
            "top5_share_pct": round(top5_cust_pct, 2),
            "risk_assessment": cust_risk,
        },
        "vendor_concentration": {
            "top1_share_pct": round(top1_vend_pct, 2),
            "top3_share_pct": round(top3_vend_pct, 2),
            "top5_share_pct": round(top5_vend_pct, 2),
            "risk_assessment": vend_risk,
        },
    }
