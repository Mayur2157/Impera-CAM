"""Module 2: Income & True Revenue Analysis.

Separates True Operating Revenue from non-revenue credits (loans, contra transfers, refunds),
identifies verified salary vs. commercial sales, and computes normalized income.
"""
from __future__ import annotations

from collections import defaultdict
import statistics
from typing import Any

from .classifier import classify_all_transactions
from .narration_rules import extract_counterparty


def analyze_income(txns: list[dict], customer_name: str = "") -> dict[str, Any]:
    # Ensure all txns are classified
    if not txns or "category" not in txns[0]:
        annotated = classify_all_transactions(txns, customer_name)
    else:
        annotated = txns

    credits = [t for t in annotated if t.get("credit") and t["credit"] > 0]
    gross_credits = sum(float(t["credit"]) for t in credits)

    # 1. Separate Inflow Categories
    salary_txns = []
    biz_receipt_txns = []
    loan_disbursals = []
    self_transfers = []
    refunds = []
    interest_inflows = []
    other_credits = []

    for t in credits:
        cat = t.get("category", "")
        amt = float(t["credit"])
        if cat == "SALARY":
            salary_txns.append(t)
        elif cat in ("BUSINESS_RECEIPT", "CASH_DEPOSIT"):
            biz_receipt_txns.append(t)
        elif cat == "LOAN_DISBURSEMENT":
            loan_disbursals.append(t)
        elif cat == "SELF_TRANSFER_CR":
            self_transfers.append(t)
        elif cat == "REFUND_REVERSAL":
            refunds.append(t)
        elif cat == "INTEREST_INCOME":
            interest_inflows.append(t)
        else:
            other_credits.append(t)

    # True Operating Revenue = Verified Salary + Business Trade Receipts + Cash Deposits
    true_operating_revenue = sum(float(t["credit"]) for t in salary_txns + biz_receipt_txns)
    total_loan_disbursements = sum(float(t["credit"]) for t in loan_disbursals)
    total_self_transfers = sum(float(t["credit"]) for t in self_transfers)
    total_refunds = sum(float(t["credit"]) for t in refunds)
    total_interest = sum(float(t["credit"]) for t in interest_inflows)

    # 2. Salary Analysis
    is_salaried = len(salary_txns) >= 1
    detected_employer = None
    avg_salary = 0.0
    if is_salaried:
        emp_counts = defaultdict(int)
        for t in salary_txns:
            emp_counts[t.get("counterparty", "Corporate")] += 1
        detected_employer = max(emp_counts.items(), key=lambda x: x[1])[0]
        sal_amts = [float(t["credit"]) for t in salary_txns]
        avg_salary = statistics.median(sal_amts) if sal_amts else 0.0

    # 3. Monthly Revenue Trajectory
    monthly_rev = defaultdict(float)
    monthly_gross = defaultdict(float)
    for t in credits:
        d = t.get("txn_date")
        if not d:
            continue
        m_key = d.strftime("%Y-%m")
        amt = float(t["credit"])
        monthly_gross[m_key] += amt
        if t.get("is_revenue"):
            monthly_rev[m_key] += amt

    sorted_months = sorted(set(monthly_gross.keys()) | set(monthly_rev.keys()))
    num_months = max(1, len(sorted_months))

    avg_monthly_true_revenue = true_operating_revenue / num_months
    avg_monthly_gross_inflow = gross_credits / num_months

    # Normalized Monthly Income for Underwriting
    if is_salaried and avg_salary > 0:
        normalized_income = avg_salary
        income_type = "SALARIED_NET_SALARY"
    else:
        # For business entities, normalized income is monthly verified operating revenue
        normalized_income = avg_monthly_true_revenue
        income_type = "BUSINESS_OPERATING_REVENUE"

    # Stability of true operating revenue
    rev_vals = [monthly_rev[m] for m in sorted_months if monthly_rev[m] > 0]
    if len(rev_vals) >= 3:
        mean_r = statistics.mean(rev_vals)
        std_r = statistics.stdev(rev_vals)
        cv = (std_r / mean_r) if mean_r > 0 else 0.0
        stability = "HIGH" if cv < 0.25 else ("MODERATE" if cv < 0.50 else "VOLATILE")
        growth_rate = ((rev_vals[-1] - rev_vals[0]) / rev_vals[0] * 100) if rev_vals[0] > 0 else 0.0
    elif len(rev_vals) == 2:
        mean_r = statistics.mean(rev_vals)
        std_r = statistics.stdev(rev_vals)
        cv = (std_r / mean_r) if mean_r > 0 else 0.0
        stability = "PROVISIONAL (2 Months)" if cv < 0.35 else "VOLATILE (2 Months)"
        growth_rate = ((rev_vals[-1] - rev_vals[0]) / rev_vals[0] * 100) if rev_vals[0] > 0 else 0.0
    else:
        cv = 0.0
        stability = "INSUFFICIENT_DATA (Single Month)" if rev_vals else "NO_REVENUE_DETECTED"
        growth_rate = 0.0

    # Recurring credit counterparties
    cp_credits = defaultdict(list)
    for t in (salary_txns + biz_receipt_txns):
        cp = t.get("counterparty") or "Unknown"
        cp_credits[cp].append(float(t["credit"]))

    recurring_sources = []
    for cp, amts in cp_credits.items():
        if len(amts) >= 2:
            recurring_sources.append({
                "counterparty": cp,
                "count": len(amts),
                "total_amount": round(sum(amts), 2),
                "avg_amount": round(sum(amts) / len(amts), 2),
            })
    recurring_sources.sort(key=lambda x: x["total_amount"], reverse=True)

    return {
        "is_salaried": is_salaried,
        "income_type": income_type,
        "detected_employer": detected_employer,
        "normalized_monthly_income": round(normalized_income, 2),
        "true_operating_revenue": round(true_operating_revenue, 2),
        "gross_bank_credits": round(gross_credits, 2),
        "avg_monthly_true_revenue": round(avg_monthly_true_revenue, 2),
        "avg_monthly_gross_inflow": round(avg_monthly_gross_inflow, 2),
        "non_revenue_inflows": {
            "loan_disbursements": round(total_loan_disbursements, 2),
            "self_transfers": round(total_self_transfers, 2),
            "tax_refunds": round(total_refunds, 2),
            "interest_credits": round(total_interest, 2),
        },
        "salary_details": {
            "transactions_count": len(salary_txns),
            "total_salary_credited": round(sum(float(t["credit"]) for t in salary_txns), 2),
            "median_monthly_salary": round(avg_salary, 2),
        },
        "income_stability": stability,
        "revenue_volatility_cv": round(cv, 4),
        "revenue_growth_rate_pct": round(growth_rate, 2),
        "recurring_sources": recurring_sources[:8],
        "monthly_breakdown": [
            {
                "month": m,
                "true_revenue": round(monthly_rev[m], 2),
                "gross_inflow": round(monthly_gross[m], 2),
            }
            for m in sorted_months
        ],
    }
