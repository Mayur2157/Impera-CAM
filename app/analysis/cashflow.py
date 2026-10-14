"""Module 5: Cash Flow Analysis.

Tracks Total Inflows, Total Outflows, Net Cash Flow, Monthly Surplus/Deficit,
and Disposable Free Cash Flow.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any


def analyze_cash_flow(txns: list[dict], total_monthly_emi: float = 0.0,
                      months_covered: float | None = None) -> dict[str, Any]:
    monthly_inflow = defaultdict(float)
    monthly_outflow = defaultdict(float)

    total_credits = 0.0
    total_debits = 0.0

    for t in txns:
        crd = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        total_credits += crd
        total_debits += deb

        d = t.get("txn_date")
        if d:
            m_key = d.strftime("%Y-%m")
            monthly_inflow[m_key] += crd
            monthly_outflow[m_key] += deb

    net_cash_flow = total_credits - total_debits
    all_months = sorted(set(monthly_inflow.keys()) | set(monthly_outflow.keys()))

    monthly_summary = []
    surplus_months = 0
    deficit_months = 0

    for m in all_months:
        inf = monthly_inflow[m]
        outf = monthly_outflow[m]
        net = inf - outf
        ratio = (inf / outf) if outf > 0 else (10.0 if inf > 0 else 1.0)
        if inf == 0 and outf == 0:
            status = "NO ACTIVITY"
        elif net > 0:
            status = "SURPLUS"
            surplus_months += 1
        elif net < 0:
            status = "DEFICIT"
            deficit_months += 1
        else:
            status = "BREAKEVEN"

        monthly_summary.append({
            "month": m,
            "inflow": round(inf, 2),
            "outflow": round(outf, 2),
            "net_flow": round(net, 2),
            "inflow_outflow_ratio": round(ratio, 2),
            "status": status,
        })

    # Disposable cash flow = Net flow after detected monthly EMIs
    # days covered / 30.4: a partial first or last month is not a whole month
    num_months = months_covered or len(all_months) or 1
    # net cash flow already has the EMIs paid in it (they are debits); taking
    # them off again would count them twice
    disposable_cash_flow = net_cash_flow

    avg_monthly_inflow = total_credits / num_months
    avg_monthly_outflow = total_debits / num_months
    avg_monthly_net = net_cash_flow / num_months

    return {
        "total_inflows": round(total_credits, 2),
        "total_outflows": round(total_debits, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "avg_monthly_inflow": round(avg_monthly_inflow, 2),
        "avg_monthly_outflow": round(avg_monthly_outflow, 2),
        "avg_monthly_net": round(avg_monthly_net, 2),
        "disposable_cash_flow": round(disposable_cash_flow, 2),
        "surplus_months_count": surplus_months,
        "deficit_months_count": deficit_months,
        "overall_status": "SURPLUS" if net_cash_flow >= 0 else "DEFICIT",
        "monthly_summary": monthly_summary,
    }
