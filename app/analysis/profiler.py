"""Master Financial Profiler & Credit Appraisal Memorandum (CAM) Engine.

Implements the 8-component 100-point underwriting scoring matrix:
1. Cash-flow stability & margin: 20%
2. Liquidity / ABB: 15%
3. Debt / repayment capacity (DSCR/FOIR): 15%
4. EMI repayment regularity: 10%
5. Overdraft utilization & facility compliance: 15%
6. Bounce / return behavior: 10%
7. Transaction risk / AML: 10%
8. Income stability & concentration: 5%
Total = 100%
"""
from __future__ import annotations

from typing import Any

from .classifier import classify_all_transactions
from .eligible_income import analyze_eligible_income
from .health import analyze_account_health
from .income import analyze_income
from .expenses import analyze_expenses
from .debt import analyze_debt
from .account_type import resolve_borrower_type
from .cashflow import analyze_cash_flow
from .channels import analyze_channels
from .counterparties import analyze_counterparties
from .risk import analyze_risk
from .fraud_aml import analyze_fraud_and_aml
from .business import analyze_business


def _aml_flag(patterns: int, round_pct: float) -> str:
    """Say what was actually seen: near-threshold cash patterns, round-figure
    transactions, or both — never '0 structuring patterns' as a red flag."""
    parts = []
    if patterns:
        parts.append(f"{patterns} potential cash structuring pattern(s) — review")
    if round_pct > 25.0:
        parts.append(f"round-figure transactions are {round_pct:.1f}% of value")
    return "; ".join(parts).capitalize()


def _months_covered(txns: list[dict], info: dict, meta: dict | None = None):
    """(months, statement end, basis). Months = days in the period / 30.4.

    1. The statement period printed in the header, when there is one. Quiet
       months inside it count (Union: 01/04/2020-31/03/2021 is 12 months even
       though the first transaction is in June). A transaction printed just
       outside it widens the period to include it.
    2. No header period: the first to the last ACTUAL transaction (rows with
       an amount; opening/closing balance and balance-forward lines are not
       transactions).
    A PDF that holds only part of its statement (flagged PARTIAL: pages or
    dates missing) is measured by its transactions, because the header period
    describes months the PDF does not contain."""
    dates = [t["txn_date"] for t in txns if t.get("txn_date") and (t.get("debit") or t.get("credit"))]
    if not dates:
        return 1.0, None, "no dated transactions"
    first, last = min(dates), max(dates)

    def as_date(v):
        if not hasattr(v, "year"):
            return None
        return v.date() if hasattr(v, "date") and callable(v.date) else v
    pf, pt = as_date(info.get("period_from")), as_date(info.get("period_to"))
    partial = bool((meta or {}).get("is_partial"))
    if pf and pt and pt >= pf and not partial:
        start, end = min(pf, first), max(pt, last)
        basis = f"statement period in header ({pf:%d-%b-%Y} to {pt:%d-%b-%Y})"
        if (start, end) != (pf, pt):
            basis += f", widened to {start:%d-%b-%Y} to {end:%d-%b-%Y} to include all transactions"
    elif as_date(info.get("opening_balance_date")) and not partial:
        # no header period, but the opening / balance-forward line dates where
        # the statement's coverage begins (ebrcpt: 16 Jun, first transaction 17 Jun)
        ob = as_date(info.get("opening_balance_date"))
        start, end = min(ob, first), last
        basis = (f"statement coverage ({start:%d-%b-%Y} balance-forward line to {end:%d-%b-%Y} "
                 f"last transaction; no statement period in header)")
    else:
        start, end = first, last
        why = "PDF holds only part of the statement" if (pf and pt and partial) else "no statement period in header"
        basis = f"first to last transaction ({start:%d-%b-%Y} to {end:%d-%b-%Y}; {why})"
    days = (end - start).days + 1
    return max(days / 30.4, 0.1), end, basis


def _period_fields(txns: list[dict], info: dict) -> dict:
    """Two views of the dates. Statement coverage: where the statement's
    balances begin and end (header period, else the opening / balance-forward
    line, else the first transaction). Transaction period: the first and last
    actual transaction, which the analysis measures when the header prints no
    period (see _months_covered)."""
    dates = [t["txn_date"] for t in txns if t.get("txn_date") and (t.get("debit") or t.get("credit"))]
    first, last = (min(dates), max(dates)) if dates else (None, None)
    pf, pt = info.get("period_from"), info.get("period_to")
    start = pf or info.get("opening_balance_date") or first
    end = pt or last

    def fmt(d):
        return d.strftime("%d-%b-%Y") if d else None
    return {
        "statement_coverage_start": fmt(start),
        "statement_coverage_end": fmt(end),
        "statement_coverage_source": ("header period" if pf else
                                      "opening / balance-forward line" if info.get("opening_balance_date") else
                                      "first transaction"),
        "transaction_period_start": fmt(first),
        "transaction_period_end": fmt(last),
    }


def generate_financial_profile(
    txns: list[dict],
    info: dict | None = None,
    meta: dict | None = None,
    issues: list | None = None,
) -> dict[str, Any]:
    info = info or {}
    meta = meta or {}
    issues = issues or []
    cust_name = str(info.get("customer_name") or "")

    # Layer 3a: what kind of account, and who holds it. Balances and header
    # evidence only, so it comes before classification, which needs the
    # answer (a firm's customers are not 'personal credits')
    health_data = analyze_account_health(txns, info)
    facility_type = health_data["facility_type"]
    # who holds the account (DSCR vs FOIR, persona) is a separate question
    # from what kind of account it is (facility scoring)
    borrower = resolve_borrower_type(info, health_data.get("account_type", "UNKNOWN"),
                                     health_data.get("account_type_confidence", "NONE"))

    # Layer 3b: Classify every transaction
    classified_txns = classify_all_transactions(
        txns, customer_name=cust_name, info={**info, "borrower_type": borrower["borrower_type"]})
    months_covered, statement_end, period_basis = _months_covered(txns, info, meta)
    # one months figure, shown and divided by alike
    months_covered = round(months_covered, 2)

    # Layer 4: Analytics

    # 2. Eligible Income
    eligible_income_data = analyze_eligible_income(
        classified_txns, customer_name=cust_name, facility_type=facility_type,
        months_covered=months_covered, is_business=borrower["borrower_type"] == "BUSINESS",
    )

    # 3. Income Analysis
    income_data = analyze_income(classified_txns, customer_name=cust_name)

    # 4. Expenses
    expense_data = analyze_expenses(classified_txns)

    # 5. Debt, FOIR & DSCR (using Eligible Income)
    debt_data = analyze_debt(
        classified_txns,
        income_data=income_data,
        eligible_income_data=eligible_income_data,
        customer_name=cust_name,
        statement_end=statement_end,
        months_covered=months_covered,
    )

    # Compute Business Estimated Operating Surplus:
    # Operating Surplus = Eligible Business Receipts - Operating Expenses - Debt Service
    monthly_debt_service = debt_data.get("total_monthly_debt_service", 0.0)
    monthly_op_exp = eligible_income_data.get("monthly_operating_expenses", 0.0)
    monthly_receipts = eligible_income_data.get("monthly_eligible_income", 0.0)
    monthly_operating_cash = monthly_receipts - monthly_op_exp
    estimated_monthly_operating_surplus = monthly_operating_cash - monthly_debt_service
    eligible_income_data["monthly_debt_service"] = monthly_debt_service
    eligible_income_data["monthly_operating_cash"] = round(monthly_operating_cash, 2)
    eligible_income_data["estimated_operating_surplus"] = round(estimated_monthly_operating_surplus, 2)

    # 6. Cash Flow
    cashflow_data = analyze_cash_flow(
        classified_txns, total_monthly_emi=debt_data["total_monthly_emi_obligation"],
        months_covered=months_covered,
    )

    # 7. Channels
    channel_data = analyze_channels(classified_txns)

    # 8. Counterparties
    counterparty_data = analyze_counterparties(classified_txns, customer_name=cust_name)

    # 9. Risk & Bounces
    risk_data = analyze_risk(classified_txns, health_data=health_data, customer_name=cust_name)

    # 10. Fraud & AML (with Confidence Scoring)
    fraud_aml_data = analyze_fraud_and_aml(classified_txns, customer_name=cust_name)

    # 11. Business Trends
    business_data = analyze_business(
        classified_txns,
        counterparty_data["top_inward_parties"],
        counterparty_data["top_outward_parties"],
        monthly_operating=eligible_income_data.get("monthly_operating"),
    )

    # 12. Statement Validation
    score_val = meta.get("score", 1.0)
    validation_data = {
        "balance_chain_score": float(score_val),
        "balance_chain_pass_rate_pct": round(float(score_val) * 100, 2),
        "chain_orientation": meta.get("mode", "asis"),
        "relinking_needed": bool(meta.get("recon", 0) > 0),
        "statement_completeness": meta.get("completeness", "COMPLETE"),
        "flagged_issues_count": len(issues),
        "opening_balance": float(meta["opening"]) if meta.get("opening") is not None else None,
        "closing_balance": float(meta["closing"]) if meta.get("closing") is not None else None,
    }

    # ----------------------------------------------------------------------
    # Layer 5: Calibrated 8-Component Scoring Matrix (100 pts)
    # ----------------------------------------------------------------------
    scorecard = {}
    strengths = []
    red_flags = []
    hard_caps = []

    # what the header could not tell us, said out loud
    if str(meta.get("column_headers", "")).startswith("matched by words"):
        red_flags.append("Unfamiliar statement layout: column headers were matched by their words, not known "
                         "labels — check a sample of rows against the PDF")
    if not cust_name:
        red_flags.append("Holder name not found in the header: own-account transfers can only be matched by "
                         "account number, e-mail or mobile, and firm vs individual is less certain — review")
        # own and related money cannot be told from income without the holder's
        # name, so a missing name must never read as a better borrower
        hard_caps.append((45.0, "Holder not identified — own-account and related-party money "
                                "cannot be separated from income"))
    for c in health_data.get("account_type_conflicts") or []:
        red_flags.append(f"Account type conflict: resolved {health_data.get('account_type')} but evidence says {c}")
    for w in health_data.get("account_type_warnings") or []:
        red_flags.append(f"Account type: {w}")
    if health_data.get("account_type_confidence") in ("LOW", "NONE"):
        red_flags.append(f"Account type {health_data.get('account_type')} is {health_data.get('account_type_confidence').lower()} "
                         f"confidence ({health_data.get('account_type_evidence')})")

    # 1. Cash-Flow Stability & Margin (20 pts)
    # 1. Operating Cash-Flow Stability & Margin (20 pts)
    # Evaluates whether the entity's true operating receipts cover operating expenses & debt service
    m_inc = eligible_income_data.get("monthly_eligible_income", 0.0)
    m_exp = eligible_income_data.get("monthly_operating_expenses", 0.0)
    m_debt = debt_data.get("total_monthly_debt_service", 0.0)
    # When most operating payments were set aside with unverified cash (Bharat:
    # ₹5.57 Cr of Airtel float paid from cash), the verified margin is what is
    # left after removing them, not the business's margin. It is N/M, and this
    # component is scored on all money in and out instead.
    v_inc, v_exp = m_inc, m_exp          # verified basis, used by the DSCR checks below
    margin_basis = "verified"
    if (eligible_income_data.get("cash_funded_share_of_expenses_pct") or 0.0) >= 50.0:
        margin_basis = "all flows"
        m_inc = m_inc + (eligible_income_data.get("monthly_cash_deposits") or 0.0)
        m_exp = m_exp + (eligible_income_data.get("monthly_cash_funded_payments") or 0.0)
    m_surplus = m_inc - m_exp - m_debt

    surplus_margin_pct = (m_surplus / m_inc * 100.0) if m_inc > 0 else 0.0

    monthly_summaries = cashflow_data.get("monthly_summary", [])
    total_months = max(1, len(monthly_summaries))
    # Deficit months on the eligible basis, like every other income figure;
    # gross net flow (own transfers, loans, cash) would contradict the margin
    monthly_operating = eligible_income_data.get("monthly_operating") or []
    if monthly_operating:
        total_months = len(monthly_operating)
    deficit_months = sum(1 for m in monthly_operating if m["operating_net"] < 0)
    deficit_freq_pct = (deficit_months / total_months) * 100.0

    basis_note = ("; on all money in and out incl. unverified cash — verified-basis margin N/M, "
                  "most expenses were set aside with the cash") if margin_basis == "all flows" else ""
    income_meaningful = eligible_income_data.get("income_meaningful", True)
    if not income_meaningful:
        gross_m = (eligible_income_data.get("gross_credits") or 0.0) / max(0.1, months_covered)
        c1 = 0.0
        red_flags.append(f"No meaningful eligible income: ₹{m_inc:,.2f}/mo of eligible receipts against "
                         f"₹{gross_m:,.2f}/mo gross inflows; operating result -₹{abs(m_surplus):,.2f}/mo "
                         f"(margin and debt-to-revenue not meaningful)")
        hard_caps.append((45.0, "No meaningful eligible income"))
    elif m_surplus >= 0:
        if surplus_margin_pct >= 20.0:
            c1 = 20.0
            strengths.append(f"Strong Operating Cash Surplus: +₹{m_surplus:,.2f}/mo (+{surplus_margin_pct:.1f}% margin{basis_note})")
        elif surplus_margin_pct >= 10.0:
            c1 = 16.0
            strengths.append(f"Comfortable Operating Surplus: +₹{m_surplus:,.2f}/mo (+{surplus_margin_pct:.1f}% margin{basis_note})")
        else:
            c1 = 12.0
            strengths.append(f"Tight Operating Surplus: +₹{m_surplus:,.2f}/mo (+{surplus_margin_pct:.1f}% margin{basis_note})")
    else:
        # Operating Deficit
        def_amt = abs(m_surplus)
        def_pct = abs(surplus_margin_pct)
        if def_pct <= 5.0:
            c1 = 6.0
            red_flags.append(f"Mild Operating Deficit: -₹{def_amt:,.2f}/mo ({def_pct:.1f}% of revenue{basis_note})")
        elif def_pct <= 25.0:
            c1 = 2.0
            red_flags.append(f"Sustained Operating Deficit: -₹{def_amt:,.2f}/mo ({def_pct:.1f}% of revenue{basis_note})")
        else:
            c1 = 0.0
            red_flags.append(f"Severe Operating Deficit: -₹{def_amt:,.2f}/mo ({def_pct:.1f}% of revenue{basis_note})")
            hard_caps.append((55.0, f"Severe Operating Cash Deficit ({def_pct:.1f}% of revenue{basis_note})"))

    if deficit_freq_pct >= 50.0 and c1 > 2.0:
        c1 = max(0.0, c1 - 4.0)
        red_flags.append(f"Frequent Operating Deficit Months ({deficit_months}/{total_months} months: "
                         f"eligible receipts below operating expenses + debt service)")

    scorecard["cashflow_margin_score"] = round(c1, 1)

    # 2. Liquidity / ABB (15 pts)
    abb = health_data["abb"]
    avg_monthly_outflow = cashflow_data["avg_monthly_outflow"] or 1.0
    buffer_months = (abb / avg_monthly_outflow) if abb > 0 else 0.0

    limit_known = health_data.get("estimated_sanctioned_limit") is not None
    unscored = []
    unscored_reasons: dict[str, str] = {}      # scorecard key → why it was not scored
    if facility_type == "OVERDRAFT_CC" and not limit_known:
        # No printed limit: turnover-to-limit cannot be measured, so the
        # component is left out and the total is rescaled (not guessed)
        c2 = None
        unscored.append("Liquidity (OD limit not printed)")
        unscored_reasons["liquidity_abb_score"] = "OD limit not printed in statement"
    elif facility_type == "OVERDRAFT_CC":
        # For OD, liquidity is judged by healthy turnover to limit and buffer
        churn = health_data.get("credit_turnover_to_limit") or 0.0
        if churn >= 4.0:
            c2 = 12.0
            if abb >= 0 and m_surplus >= 0:
                strengths.append(f"High Credit Turnover Relative to OD Limit: {churn:.1f}x (Norm: 4-6x)")
            elif abb < 0 and m_surplus < 0 and churn > 10.0:
                red_flags.append(f"High Credit Turnover Relative to OD Limit ({churn:.1f}x) coexisting with Deep Overdraft (ABB: ₹{abb:,.2f}) and Cash Deficit")
        elif churn >= 2.5:
            c2 = 8.0
        else:
            c2 = 2.0
            red_flags.append(f"Sluggish Credit Turnover to OD Limit ({churn:.1f}x vs 4-6x norm)")
    else:
        if buffer_months >= 2.0:
            c2 = 15.0
            strengths.append(f"High Liquidity Buffer: ABB covers {buffer_months:.1f} months of expenses")
        elif buffer_months >= 1.0:
            c2 = 10.0
            strengths.append(f"Adequate Liquidity Buffer: ABB covers {buffer_months:.1f} months of expenses")
        elif buffer_months > 0.0:
            c2 = 5.0
            red_flags.append(f"Tight Liquidity: ABB covers only {buffer_months:.1f} months of expenses")
        else:
            c2 = 0.0
    scorecard["liquidity_abb_score"] = round(c2, 1) if c2 is not None else None

    # Sustained operating deficit with inadequate liquidity cushion hard cap
    if m_surplus < 0 and buffer_months < 0.5 and facility_type != "OVERDRAFT_CC":
        hard_caps.append((60.0, f"Sustained operating deficit (₹{abs(m_surplus):,.2f}/mo) + inadequate liquidity buffer (< 0.5 months, ABB ₹{abb:,.2f}) → Maximum allowable score capped at 60.0 (MODERATE RISK)"))

    # 3. Debt / Repayment Capacity: DSCR / FOIR (15 pts)
    dscr = debt_data.get("dscr")
    # an individual's account is judged on retail FOIR, salaried or not
    is_salaried = income_data["is_salaried"]
    is_retail = is_salaried or not eligible_income_data.get("is_business")
    foir = debt_data["foir_percentage"]

    if debt_data.get("total_monthly_debt_service", 0.0) == 0 and not debt_data.get("loans_detected_count"):
        # no debt to service: the component tests nothing, so it is not scored
        c3 = None
        unscored.append("Debt repayment capacity (no debt to service)")
        unscored_reasons["debt_capacity_score"] = "No debt to service in statement"
        strengths.append("No term loan, card or OD interest obligations observed")
    elif is_retail and foir is None:
        c3 = 0.0
        red_flags.append("Retail FOIR not meaningful: no eligible income")
    elif is_retail:
        if foir <= 30.0:
            c3 = 15.0
            strengths.append(f"Comfortable Retail FOIR: {foir:.1f}%")
        elif foir <= 45.0:
            c3 = 10.0
            strengths.append(f"Manageable Retail FOIR: {foir:.1f}%")
        elif foir <= 55.0:
            c3 = 5.0
            red_flags.append(f"Elevated Retail FOIR: {foir:.1f}%")
        else:
            c3 = 0.0
            red_flags.append(f"Excessive Retail Debt Burden: FOIR is {foir:.1f}%")
            hard_caps.append((50.0, "Retail FOIR exceeds 55%"))
    else:
        tot_debt_svc = debt_data.get("total_monthly_debt_service", 0.0)
        raw_dscr = debt_data.get("raw_dscr")
        if tot_debt_svc == 0:
            c3 = 15.0
            strengths.append("Debt Free: No Term Loan or OD Financing Obligations (Debt Burden: 0%)")
        elif dscr is not None:
            if dscr >= 1.5:
                c3 = 15.0
                strengths.append(f"Strong Debt Service Coverage: DSCR {dscr:.2f}x (>=1.5x)")
            elif dscr >= 1.2:
                c3 = 11.0
                strengths.append(f"Adequate Debt Service Coverage: DSCR {dscr:.2f}x")
            elif dscr >= 1.0:
                c3 = 6.0
                red_flags.append(f"Borderline Debt Service Coverage: DSCR {dscr:.2f}x")
            else:
                c3 = 0.0
                red_flags.append(f"Debt Service Deficit: DSCR is {dscr:.2f}x (<1.0x indicates cash shortfall)")
                hard_caps.append((50.0, "Debt Service Coverage Deficit (DSCR < 1.0x)"))
        else:
            # Negative operating cash flow (CADS < 0)
            c3 = 0.0
            raw_str = f"{raw_dscr:.2f}x" if raw_dscr is not None else "Negative"
            red_flags.append(f"Operating Cash Deficit: DSCR is N/M (Raw Coverage: {raw_str} indicates operating cash deficit)")
            # the cap follows the size of the deficit: a 3.7% shortfall should not
            # be capped harder than a severe one (which is capped at 55 above)
            op_deficit_pct = ((v_exp - v_inc) / v_inc * 100.0) if v_inc > 0 else 100.0
            if op_deficit_pct >= 10.0:
                hard_caps.append((45.0, f"Operating Cash Flow Deficit (DSCR N/M, {op_deficit_pct:.1f}% of income)"))

        # Also add strength/flag on Business Debt-to-Revenue
        if foir is None:
            pass
        elif foir <= 15.0:
            strengths.append(f"Manageable Business Debt-to-Revenue: {foir:.2f}% of monthly receipts")
        elif foir > 40.0:
            red_flags.append(f"Elevated Business Debt-to-Revenue: {foir:.2f}% of monthly receipts")

    scorecard["debt_capacity_score"] = round(c3, 1) if c3 is not None else None

    # A new or larger loan: the EMI now running is well above what the period
    # paid on average, so coverage will be tighter than the period shows
    if debt_data.get("forward_emi_exceeds_paid"):
        fwd = debt_data["total_monthly_emi_obligation"]
        paid = debt_data.get("monthly_emi_paid", 0.0)
        fwd_service = fwd + debt_data.get("total_monthly_interest_obligation", 0.0)
        cash = v_inc - v_exp
        fwd_dscr = f"{cash / fwd_service:.2f}x" if fwd_service and cash > 0 else "N/M"
        red_flags.append(f"Current EMI on active loans ₹{fwd:,.2f}/mo is above the ₹{paid:,.2f}/mo paid on "
                         f"average in the period (new or larger loan); DSCR on current EMIs would be {fwd_dscr}")

    # 4. Loan EMI Repayment Regularity (10 pts)
    # Every loan repaid during the statement counts, closed or not: a bounce
    # on a loan that has since stopped is still a bounce in this period.
    # With no loans at all there is nothing to test, so no free points.
    bounces_on_loan = debt_data.get("loan_emi_bounces_count", 0)
    if debt_data.get("loans_detected_count", debt_data["active_loans_count"]) == 0:
        c4 = None
        unscored.append("EMI regularity (no loan repayments in statement)")
        unscored_reasons["emi_regularity_score"] = "No loan repayments in statement"
    elif bounces_on_loan == 0 and debt_data.get("unlinked_returns_while_loans_live"):
        # own payments bounced while loans were being repaid, but nothing ties
        # them to a loan: neither 'regular' nor proven EMI bounces (they are
        # still counted under bounce behaviour)
        c4 = None
        n = debt_data["unlinked_returns_while_loans_live"]
        unscored.append(f"EMI regularity ({n} return(s) during loan repayments, loan link unknown)")
        unscored_reasons["emi_regularity_score"] = (f"{n} own-payment return(s) while loans were being repaid; "
                                                    f"not enough evidence to tie them to a loan or rule it out")
    elif bounces_on_loan == 0 and max((l["installments_detected"] for l in debt_data.get("loans", [])), default=0) < 3:
        # one or two instalments with no bounce is not a repayment history
        c4 = None
        unscored.append("EMI regularity (limited history — no bounce observed)")
        unscored_reasons["emi_regularity_score"] = "Limited history (under 3 instalments) — no bounce observed"
    elif bounces_on_loan == 0:
        c4 = 10.0
        strengths.append("Loan EMI Repayment Regularity: REGULAR — 0 EMI bounces")
    elif bounces_on_loan == 1:
        c4 = 3.0
        red_flags.append("Loan EMI Repayment Regularity: 1 Loan Repayment / Mandate Bounce Detected")
    else:
        c4 = 0.0
        red_flags.append(f"Loan EMI Repayment Regularity: {bounces_on_loan} Loan Repayment Bounces Detected")
        hard_caps.append((45.0, "Multiple Loan Repayment Bounces"))
    scorecard["emi_regularity_score"] = round(c4, 1) if c4 is not None else None

    # 5. Overdraft Utilization & Facility Compliance (15 pts)
    neg_days = health_data["negative_balance_days"]
    total_days = health_data["total_days"] or 1

    if facility_type == "OVERDRAFT_CC" and not limit_known:
        c5 = None
        unscored.append("Limit utilisation (OD limit not printed)")
        unscored_reasons["facility_compliance_score"] = "OD limit not printed in statement"
    elif facility_type == "OVERDRAFT_CC":
        avg_util = health_data.get("average_limit_utilization_pct") or 0.0
        peak_util = health_data.get("peak_limit_utilization_pct") or 0.0
        if avg_util < 75.0:
            c5 = 15.0
            strengths.append(f"Optimal Overdraft Limit Utilization ({avg_util:.1f}%)")
        elif avg_util <= 85.0:
            c5 = 10.0
            strengths.append(f"Acceptable Overdraft Limit Utilization ({avg_util:.1f}%)")
        elif avg_util <= 92.0:
            c5 = 5.0
            red_flags.append(f"High Overdraft Limit Utilization ({avg_util:.1f}%)")
        else:
            c5 = 0.0
            red_flags.append(f"Near-Full Overdraft Limit Utilization ({avg_util:.1f}%, Peak: {peak_util:.1f}%)")
            hard_caps.append((55.0, "High Overdraft Utilization (>92%)"))
    else:
        # Savings / current: there is no limit to comply with, so the component
        # is not applicable (not 15 free points). A negative balance on such an
        # account is still an observed breach and is flagged and capped.
        c5 = None
        if facility_type == "UNKNOWN":
            unscored.append("Facility compliance (account type unknown — cannot be assessed)")
            unscored_reasons["facility_compliance_score"] = "Account type unknown — cannot be assessed"
        else:
            unscored.append(f"Facility compliance (not applicable to a {facility_type.lower()} account)")
            unscored_reasons["facility_compliance_score"] = f"Not applicable to a {facility_type.lower()} account"
        if neg_days == 0:
            strengths.append("Zero Negative Balance Days on Account")
        elif neg_days <= 5:
            red_flags.append(f"{neg_days} Negative Balance Days on Account")
            hard_caps.append((60.0, "Negative balance on an account with no overdraft facility"))
        else:
            red_flags.append(f"{neg_days} Negative Balance Days on Unapproved Account")
            hard_caps.append((35.0, "Unauthorized Overdraft on Retail/Current Account"))
    scorecard["facility_compliance_score"] = round(c5, 1) if c5 is not None else None

    # 6. Overall Banking Payment Behavior: Bounce / Return Behavior (10 pts)
    outward_bounces = risk_data["outward_bounces_count"]
    if outward_bounces == 0:
        c6 = 10.0
        strengths.append("Overall Banking Payment Behavior: REGULAR — 0 Outward / ECS Bounces")
    elif outward_bounces == 1:
        c6 = 3.0
        red_flags.append("Overall Banking Payment Behavior: 1 Outward Payment / ECS Bounce Detected")
        hard_caps.append((60.0, "1 Outward Payment Bounce Detected"))
    else:
        c6 = 0.0
        red_flags.append(f"Overall Banking Payment Behavior: {outward_bounces} Outward / ECS Bounces Detected")
        hard_caps.append((45.0, f"{outward_bounces} Outward Payment Bounces"))
    scorecard["bounce_behavior_score"] = round(c6, 1)

    # 7. Transaction Risk / AML (10 pts)
    struct_alerts = fraud_aml_data.get("structuring_alerts", [])
    high_conf_struct = sum(1 for s in struct_alerts if s.get("confidence_level") == "HIGH")
    med_conf_struct = sum(1 for s in struct_alerts if s.get("confidence_level") == "MEDIUM")
    if eligible_income_data.get("cash_collection_model"):
        # when cash IS the business, near-threshold deposits are expected; the
        # pattern is still flagged for review but is not treated as strong evidence
        med_conf_struct += high_conf_struct
        high_conf_struct = 0
    round_pct = fraud_aml_data.get("round_amount_share_pct", 0.0)

    if high_conf_struct > 0:
        c7 = 0.0
        red_flags.append(f"{high_conf_struct} potential cash structuring pattern(s), strong indicators — review")
        hard_caps.append((65.0, "Potential cash structuring pattern (strong indicators) — review"))
    elif med_conf_struct >= 3 or round_pct > 40.0:
        c7 = 2.0
        red_flags.append(_aml_flag(med_conf_struct, round_pct))
    elif med_conf_struct >= 1 or round_pct > 25.0:
        c7 = 6.0
        red_flags.append(_aml_flag(med_conf_struct, round_pct))
    else:
        c7 = 10.0
        strengths.append("Clean Transaction Pattern: Low AML / Structuring Risk")
    scorecard["transaction_risk_score"] = round(c7, 1)

    # 8. Income Stability & Concentration (5 pts)
    num_months = max(1, eligible_income_data.get("months_count", 1))
    top1_share = eligible_income_data["concentration"]["top1_share_pct"]
    if not income_meaningful:
        c8 = None
        unscored.append("Income concentration (no meaningful eligible income)")
        unscored_reasons["income_concentration_score"] = "No meaningful eligible income"
    elif income_data.get("is_salaried"):
        # one employer paying the salary is the normal shape of salaried income
        c8 = None
        unscored.append("Income concentration (salaried: a single employer is expected)")
        unscored_reasons["income_concentration_score"] = "Salaried income — a single employer is expected"
    elif top1_share <= 35.0:
        c8 = 5.0
        if num_months >= 3:
            strengths.append(f"Diversified Revenue: Top Payer accounts for {top1_share:.1f}% of eligible operating receipts")
        else:
            strengths.append(f"Diversified Inflows in Audit Window: Top Payer accounts for {top1_share:.1f}% of eligible operating receipts ({num_months} mo)")
    elif top1_share <= 55.0:
        c8 = 3.0
    else:
        c8 = 1.0
        red_flags.append(f"High Concentration Risk: Top Payer accounts for {top1_share:.1f}% of eligible operating receipts")
    scorecard["income_concentration_score"] = round(c8, 1) if c8 is not None else None

    # 9. Classification coverage: if much of the money could not be
    #    identified, the score cannot be trusted however good it looks
    gross = (eligible_income_data.get("gross_credits") or 0.0) + (eligible_income_data.get("gross_debits") or 0.0)
    unclassified_amt = sum(float(t.get("credit") or t.get("debit") or 0)
                           for t in classified_txns if t.get("category", "").startswith("UNCLASSIFIED"))
    unclassified_pct = (unclassified_amt / gross * 100.0) if gross else 0.0
    if unclassified_pct > 15.0:
        red_flags.append(f"Insufficient classification: {unclassified_pct:.1f}% of flows have no identifiable party or rule")
        hard_caps.append((60.0, f"Insufficient classification ({unclassified_pct:.1f}% of flows unclassified)"))

    # 10. Unverified cash: the ratios above use verified receipts only, so
    #     when most of the money is cash of unknown source they describe a
    #     small part of the account; say so, and when cash is most of the
    #     inflow do not let the score read better than moderate
    cash_share = eligible_income_data.get("cash_share_of_inflows_pct") or 0.0
    if cash_share >= 25.0:
        unverified_cash = eligible_income_data.get("unverified_cash_deposits") or 0.0
        incl = debt_data.get("dscr_incl_unverified_cash")
        incl_txt = f"; DSCR would be {incl:.2f}x if it were income" if incl is not None else ""
        red_flags.append(f"Cash of unverified source: ₹{unverified_cash:,.2f} ({cash_share:.1f}% of inflows) "
                         f"is not counted as income{incl_txt} — verify the source (sales records / GST)")
        if cash_share >= 50.0:
            hard_caps.append((60.0, f"Most inflows are cash of unverified source ({cash_share:.1f}%)"))

    # credits from individuals whose purpose the statement cannot show
    pending = eligible_income_data.get("pending_review_personal_credits") or 0.0
    if pending:
        red_flags.append(
            f"Pending review: ₹{pending:,.2f} from individuals ({eligible_income_data.get('pending_review_personal_count')} "
            f"credits) — purpose unknown, not counted; income would be "
            f"₹{eligible_income_data.get('monthly_income_if_review_accepted', 0):,.2f}/mo if accepted "
            f"(₹{eligible_income_data.get('monthly_eligible_income', 0):,.2f}/mo counted)")

    for flag in fraud_aml_data.get("business_model_flags", []):
        red_flags.append(flag)

    # Compute Total Score (components that could not be measured are left out
    # and the rest rescaled to 100)
    weights = {"cashflow_margin_score": 20, "liquidity_abb_score": 15, "debt_capacity_score": 15,
               "emi_regularity_score": 10, "facility_compliance_score": 15, "bounce_behavior_score": 10,
               "transaction_risk_score": 10, "income_concentration_score": 5}
    scored = {k: v for k, v in scorecard.items() if v is not None}
    available = sum(weights[k] for k in scored)
    total_raw_score = sum(scored.values()) * (100.0 / available) if available else 0.0
    final_score = round(total_raw_score, 1)

    # Apply Hard Capping Rules. Every triggered cap is disclosed; the one that
    # actually set the score is marked binding (a cap above the score changes nothing)
    uncapped_score = final_score
    binding = min(hard_caps, key=lambda c: c[0]) if hard_caps else None
    if binding and final_score > binding[0]:
        final_score = binding[0]
    applied_caps = [
        f"Hard Cap {cap_val:g}: {cap_reason}"
        + (" — BINDING (score capped)" if binding and (cap_val, cap_reason) == binding and uncapped_score > cap_val
           else " — not binding (score already below)")
        for cap_val, cap_reason in sorted(hard_caps)]

    final_score = max(5.0, min(100.0, final_score))

    # Calibrated Risk Rating Scale
    if final_score >= 80.0:
        grade = "LOW RISK (PRIME)"
    elif final_score >= 65.0:
        grade = "MODERATE-LOW RISK"
    elif final_score >= 50.0:
        grade = "MODERATE RISK"
    elif final_score >= 35.0:
        grade = "HIGH RISK"
    else:
        grade = "VERY HIGH RISK / STRESSED"

    # The Risk section's overall rating follows the final grade
    risk_data["overall_risk_rating"] = (
        "LOW" if final_score >= 65.0 else "MODERATE" if final_score >= 50.0 else
        "HIGH" if final_score >= 35.0 else "VERY HIGH")

    # Data Sufficiency based on days covered (not calendar months touched)
    num_months = round(months_covered, 1)
    cal_months = eligible_income_data.get("calendar_months_with_activity", 0)
    if num_months < 3:
        confidence_level = "VERY LIMITED"
    elif num_months <= 5:
        confidence_level = "LIMITED"
    elif num_months <= 11:
        confidence_level = "MODERATE"
    else:
        confidence_level = "STRONG"

    data_sufficiency = f"{confidence_level} — {num_months} months of statement"
    analysis_period = f"{num_months} Months Audited ({cal_months} calendar months with activity)"
    if num_months < 3:
        red_flags.append(f"Limited Statement Horizon: {num_months} month(s) audited — sample period too brief to verify seasonality or annualized revenue stability")

    # Persona follows the facility (from the header) and the holder, not
    # the mere presence of credits
    if is_salaried:
        persona = f"Salaried Individual ({income_data['detected_employer'] or 'Corporate'})"
    elif borrower["borrower_type"] == "BUSINESS" and facility_type == "OVERDRAFT_CC":
        persona = f"Commercial Borrower ({info.get('bank', '')} OD/CC Facility)"
    elif borrower["borrower_type"] == "BUSINESS":
        persona = "Commercial / Business Entity"
    elif borrower["borrower_type"] == "INDIVIDUAL":
        persona = f"Individual ({facility_type.replace('_', '/').title()} Account)"
    else:
        persona = "Unknown (holder not identified)"

    return {
        "executive_summary": {
            "account_holder": cust_name or "N/A",
            "bank_name": info.get("bank") or "N/A",
            "account_number": str(info.get("account_number") or "N/A"),
            "facility_type": facility_type,
            "facility_type_source": health_data.get("facility_type_source"),
            **{k: health_data.get(k) for k in (
                "account_type", "account_subtype", "account_type_raw", "account_type_step",
                "account_type_confidence", "account_type_evidence", "account_type_conflicts",
                "account_type_warnings")},
            **borrower,
            "customer_persona": persona,
            "unscored_components": unscored,
            "unscored_reasons": unscored_reasons,
            "unclassified_flow_share_pct": round(unclassified_pct, 2),
            "credit_score_index": final_score,
            "risk_rating": grade,
            "months_count": num_months,
            "analysis_period": analysis_period,
            "analysis_period_basis": period_basis,
            **_period_fields(txns, info),
            "data_sufficiency": data_sufficiency,
            "analysis_confidence_level": confidence_level,
            "analysis_sample_confidence": data_sufficiency,
            "scorecard_breakdown": scorecard,
            "hard_cap_rules_applied": applied_caps,
            "score_before_caps": round(uncapped_score, 1),
            "strengths": strengths,
            "red_flags": red_flags,
            "abb": health_data["abb"],
            "income_metric_label": eligible_income_data.get("income_metric_label", "Eligible Monthly Income"),
            "observed_monthly_eligible_receipts": eligible_income_data.get("observed_monthly_eligible_receipts", eligible_income_data["monthly_eligible_income"]),
            "underwriting_income_baseline": eligible_income_data.get("underwriting_income_baseline", eligible_income_data["monthly_eligible_income"]),
            "underwriting_baseline_type": eligible_income_data.get("underwriting_baseline_type", "100% of Verified Inflows Run-Rate"),
            "monthly_eligible_income": eligible_income_data["monthly_eligible_income"],
            "true_operating_revenue": eligible_income_data["total_eligible_income"],
            "eligible_operating_receipts_identified": eligible_income_data["total_eligible_income"],
            "gross_bank_inflows": eligible_income_data["gross_credits"],
            "total_excluded_inflows": eligible_income_data["total_excluded_inflows"],
            "monthly_operating_expenses": eligible_income_data.get("monthly_operating_expenses", 0.0),
            "operating_margin_basis": margin_basis,
            # a margin is a number only on meaningful verified income, and only
            # while it reads as one: below -100% expenses are over twice income
            # (Bank of Baroda: -988%), so the ratio itself is the useful figure
            "operating_margin_pct": round(surplus_margin_pct, 2)
            if margin_basis == "verified" and m_inc > 0 and income_meaningful and surplus_margin_pct >= -100.0 else None,
            "operating_margin_nm_reason": (
                None if margin_basis == "verified" and m_inc > 0 and income_meaningful and surplus_margin_pct >= -100.0 else
                "most expenses were set aside with unverified cash; cash-flow score uses all money in and out"
                if margin_basis == "all flows" else
                "no meaningful eligible income" if not (m_inc > 0 and income_meaningful) else
                f"operating expenses and debt service are {(m_exp + m_debt) / m_inc:.1f}x eligible income"),
            "monthly_operating_cash_available": eligible_income_data.get("monthly_operating_cash", 0.0),
            "estimated_monthly_operating_surplus": eligible_income_data.get("estimated_operating_surplus", 0.0),
            "net_cash_flow": cashflow_data["net_cash_flow"],
            "active_loans_count": debt_data["active_loans_count"],
            "total_monthly_emi": debt_data["total_monthly_emi_obligation"],
            "monthly_emi_paid": debt_data.get("monthly_emi_paid", 0.0),
            "total_monthly_interest": debt_data.get("total_monthly_interest_obligation", 0.0),
            "total_monthly_debt_service": debt_data.get("total_monthly_debt_service", 0.0),
            "debt_ratio_label": debt_data.get("debt_ratio_label", "FOIR (Debt-to-Income)"),
            "foir_percentage": debt_data["foir_percentage"],
            "foir_type": debt_data["foir_calculation_type"],
            "operating_cash_coverage_ratio": debt_data.get("operating_cash_coverage_ratio"),
            "operating_cash_coverage_status": debt_data.get("operating_cash_coverage_status"),
            "debt_burden_percentage": debt_data.get("debt_burden_percentage", 0.0),
            "dscr": debt_data.get("dscr"),
            "raw_dscr": debt_data.get("raw_dscr"),
            "dscr_assessment": debt_data.get("dscr_assessment"),
            "dscr_display": debt_data.get("dscr_display"),
            "loan_emi_bounces_count": debt_data.get("loan_emi_bounces_count", 0),
            "loan_emi_regularity": debt_data.get("emi_regularity", "REGULAR — 0 EMI Bounces"),
            "total_cash_deposits": eligible_income_data.get("total_cash_deposits", 0.0),
            "monthly_cash_deposits": eligible_income_data.get("monthly_cash_deposits", 0.0),
            "unverified_cash_deposits": eligible_income_data.get("unverified_cash_deposits", 0.0),
            "verified_business_receipts": eligible_income_data.get("verified_business_receipts", 0.0),
            "cash_share_of_inflows_pct": eligible_income_data.get("cash_share_of_inflows_pct", 0.0),
            "cash_funded_payments": eligible_income_data.get("cash_funded_payments", 0.0),
            "dscr_incl_unverified_cash": debt_data.get("dscr_incl_unverified_cash"),
            "gross_debits": eligible_income_data.get("gross_debits", 0.0),
            "total_operating_expenses": eligible_income_data.get("total_operating_expenses", 0.0),
            "total_excluded_debits": eligible_income_data.get("total_excluded_debits", 0.0),
            "estimated_sanctioned_limit": health_data.get("estimated_sanctioned_limit"),
            "average_limit_utilization_pct": health_data.get("average_limit_utilization_pct"),
            "credit_turnover_to_limit": health_data.get("credit_turnover_to_limit"),
            "outward_bounces": risk_data["outward_bounces_count"],
            "statement_completeness": validation_data["statement_completeness"],
        },
        "account_health": health_data,
        "eligible_income": eligible_income_data,
        "income_analysis": income_data,
        "expense_analysis": expense_data,
        "debt_analysis": debt_data,
        "cash_flow": cashflow_data,
        "channels": channel_data,
        "counterparties": counterparty_data,
        "risk_analysis": risk_data,
        "fraud_aml": fraud_aml_data,
        "business_analysis": business_data,
        "statement_validation": validation_data,
        "annotated_transactions": classified_txns,
    }
