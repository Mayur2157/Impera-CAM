"""Eligible Income & Inflow Underwriting Analysis.

Derives Monthly Eligible Income by categorizing verified operating inflows
and systematically excluding self-transfers, loan disbursements, refunds,
and one-time capital injections.
"""
from __future__ import annotations

from collections import defaultdict
import re
import statistics
from typing import Any

from .account_type import is_entity_name
from .classifier import classify_all_transactions

_CAPITAL_RX = re.compile(r"\bCAPITAL\b|\bEQUITY\b|\bDIRECTOR\s+LOAN\b", re.I)


def _cash_funded_payments(annotated: list[dict], op_debits: list[dict],
                          window_days: int = 2) -> set[int]:
    """Operating payments that unverified cash paid for.

    Cash deposited is spent by the debits that follow it within `window_days`
    (in posting order, every debit drawing on it, so cash is never counted
    twice). A party is cash-funded when it was paid at least three times and
    at least 80% of what it received was covered that way: a settlement the
    cash feeds, not a one-off payment that happened to follow a deposit.
    Returns ids of that party's payments.
    """
    op_ids = {id(t) for t in op_debits}
    pool: list[list] = []                      # [date, unspent amount]
    paid = defaultdict(float)
    covered = defaultdict(float)
    rows = defaultdict(list)
    for t in annotated:
        d = t.get("txn_date")
        if t.get("category") == "CASH_DEPOSIT" and t.get("credit"):
            pool.append([d, float(t["credit"])])
            continue
        if not t.get("debit") or not d:
            continue
        pool = [p for p in pool if p[0] and 0 <= (d - p[0]).days <= window_days and p[1] > 0]
        need = float(t["debit"])
        got = 0.0
        for p in pool:
            take = min(need - got, p[1])
            p[1] -= take
            got += take
            if got >= need:
                break
        cp = t.get("counterparty") or "Unknown"
        if id(t) in op_ids and cp not in ("Unknown", "Cash"):
            paid[cp] += need
            covered[cp] += got
            rows[cp].append(t)
    funded = set()
    for cp, total in paid.items():
        if len(rows[cp]) >= 3 and covered[cp] >= 0.8 * total:
            funded.update(id(t) for t in rows[cp])
    return funded


def analyze_eligible_income(
    txns: list[dict],
    customer_name: str = "",
    facility_type: str = "SAVINGS",
    months_covered: float | None = None,
    is_business: bool | None = None,
) -> dict[str, Any]:
    if not txns or "category" not in txns[0]:
        annotated = classify_all_transactions(txns, customer_name)
    else:
        annotated = txns

    # business or individual comes from the borrower type (account_type.py);
    # called on its own, the same rule: a firm's name or a current / OD account
    if is_business is None:
        is_business = is_entity_name(customer_name) or facility_type in ("CURRENT", "OVERDRAFT_CC")

    credits = [t for t in annotated if t.get("credit") and t["credit"] > 0]
    debits = [t for t in annotated if t.get("debit") and t["debit"] > 0]
    gross_credits = sum(float(t["credit"]) for t in credits)

    # Inflow Bucketing
    salary_inflows = []
    business_inflows = []
    rental_inflows = []
    interest_inflows = []
    investment_inflows = []
    other_recurring = []

    # Exclusions & Funding Channels
    self_transfers = []
    loan_disbursements = []
    tax_refunds = []
    refund_reversals = []
    capital_infusions = []
    cash_deposits = []
    related_inflows = []
    personal_credits = []       # individual's account: credits from individuals, purpose unknown (review)
    bank_funded = []            # paid in by a bank: loan / OD / remittance, to review
    pass_through = []           # received and paid straight back out
    unclassified_inflows = []
    non_operating = []          # insurance payouts, deposits later returned unpaid

    # Large spike detection (> 5x median credit)
    credit_amts = [float(t["credit"]) for t in credits]
    median_credit = statistics.median(credit_amts) if credit_amts else 0.0
    large_spike_threshold = max(500000.0, median_credit * 6.0)

    # Rental income recurs from the same tenant. A one-off 'P G RENT' credit
    # when the holder pays rent themselves is a flatmate's share, not income
    # from property.
    rent_months = defaultdict(set)
    for t in credits:
        if "RENT" in (t.get("narration") or "").upper() and t.get("txn_date"):
            rent_months[t.get("counterparty")].add(t["txn_date"].strftime("%Y-%m"))
    pays_rent = any("RENT" in (t.get("narration") or "").upper() for t in debits)
    rent_payers = set() if pays_rent else {cp for cp, ms in rent_months.items() if len(ms) >= 2}

    for t in credits:
        cat = t.get("category", "")
        amt = float(t["credit"])
        narr = (t.get("narration") or "").upper()

        if cat == "SELF_TRANSFER_CR":
            self_transfers.append(t)
        elif cat == "RELATED_PARTY_CR":
            related_inflows.append(t)
        elif cat == "UNCLASSIFIED_CR":
            unclassified_inflows.append(t)
        elif cat in ("INSURANCE_PAYOUT", "RETURNED_DEPOSIT", "PERSONAL_LOAN_CR"):
            non_operating.append(t)
        elif cat == "UNKNOWN_PERSONAL_CR":
            personal_credits.append(t)
        elif cat == "BANK_FUNDED_INFLOW":
            bank_funded.append(t)
        elif cat == "PASS_THROUGH_CR":
            pass_through.append(t)
        elif cat == "LOAN_DISBURSEMENT":
            loan_disbursements.append(t)
        elif cat == "TAX_REFUND":
            tax_refunds.append(t)
        elif cat == "REFUND_REVERSAL":
            refund_reversals.append(t)
        elif _CAPITAL_RX.search(narr) and cat not in ("INTEREST_INCOME", "SALARY", "INVESTMENT_RETURN"):
            # whole words: 'INTEREST CAPITALIZED' is interest, not capital
            capital_infusions.append(t)
        elif cat == "CASH_DEPOSIT":
            # Cash deposit is a channel funding event; not counted as verified trade revenue
            # (unless cash collection IS the business, see below)
            cash_deposits.append(t)
        elif cat == "SALARY":
            salary_inflows.append(t)
        elif cat == "INTEREST_INCOME":
            interest_inflows.append(t)
        elif "RENT" in narr and amt >= 5000 and t.get("counterparty") in rent_payers:
            rental_inflows.append(t)
        elif cat == "INVESTMENT_RETURN":
            investment_inflows.append(t)
        elif cat == "BUSINESS_RECEIPT":
            # Check if this is an extreme one-time spike that shouldn't be counted as regular recurring
            if amt >= large_spike_threshold and "TRANSFER" in narr and not any(k in narr for k in ("CLIENT", "INVOICE", "BILL", "ADVANCE")):
                capital_infusions.append(t)
            else:
                business_inflows.append(t)
        else:
            other_recurring.append(t)

    # Cash deposited at a counter proves only that cash entered the account,
    # not where it came from (sales, the owner's own money, a cash loan). So
    # cash is never verified income from the statement alone: it is kept and
    # reported, but the income, surplus, DSCR and score use verified receipts.
    # A cash-heavy business account is still flagged so near-threshold
    # deposits there are read as its normal pattern, not strong evidence.
    cash_total = sum(float(t["credit"]) for t in cash_deposits)
    cash_collection_model = (is_business and gross_credits > 0 and cash_total / gross_credits >= 0.5)

    # Totals
    tot_salary = sum(float(t["credit"]) for t in salary_inflows)
    tot_biz = sum(float(t["credit"]) for t in business_inflows)
    tot_rent = sum(float(t["credit"]) for t in rental_inflows)
    tot_int = sum(float(t["credit"]) for t in interest_inflows)
    tot_inv = sum(float(t["credit"]) for t in investment_inflows)
    tot_other = sum(float(t["credit"]) for t in other_recurring)

    total_eligible_income = tot_salary + tot_biz + tot_rent + tot_int + tot_inv + tot_other

    tot_self = sum(float(t["credit"]) for t in self_transfers)
    tot_loans = sum(float(t["credit"]) for t in loan_disbursements)
    tot_refunds = sum(float(t["credit"]) for t in tax_refunds + refund_reversals)
    tot_capital = sum(float(t["credit"]) for t in capital_infusions)
    tot_cash_dep = sum(float(t["credit"]) for t in cash_deposits)
    tot_related = sum(float(t["credit"]) for t in related_inflows)
    tot_unclassified = sum(float(t["credit"]) for t in unclassified_inflows)
    tot_non_op = sum(float(t["credit"]) for t in non_operating)
    tot_personal = sum(float(t["credit"]) for t in personal_credits)
    tot_bank = sum(float(t["credit"]) for t in bank_funded)
    tot_pass = sum(float(t["credit"]) for t in pass_through)
    total_excluded = (tot_self + tot_loans + tot_refunds + tot_capital + tot_cash_dep
                      + tot_related + tot_unclassified + tot_non_op + tot_personal + tot_bank + tot_pass)

    # Months: days covered / 30.4, so a 15-day first month is half a month,
    # not a whole one. Distinct calendar months are kept for display only.
    months_seen = {t["txn_date"].strftime("%Y-%m") for t in annotated if t.get("txn_date")}
    num_months = months_covered if months_covered else max(1, len(months_seen))

    # One definition of income for the whole report: eligible external receipts
    # (salary + business receipts + other operating inflows, after excluding
    # own-account, related-party, loan, refund and unclassified credits) per
    # month covered. Surplus, DSCR, FOIR and the score all use this figure;
    # the median salary is reported beside it but never swapped in.
    observed_monthly_eligible = total_eligible_income / num_months
    monthly_eligible_income = observed_monthly_eligible
    underwriting_baseline_type = "Eligible receipts per month covered (used in every ratio)"
    median_salary = (statistics.median(float(t["credit"]) for t in salary_inflows)
                     if salary_inflows else 0.0)
    # Ratios to income mean nothing when there is next to no income: ₹1,643 a
    # month against ₹1.1 Cr of monthly inflows gives '538,205% of revenue'
    income_meaningful = monthly_eligible_income >= max(10000.0, 0.01 * gross_credits / num_months)

    # Operating expenses (excluding non-operating debits: self-transfers, loan EMIs, interest, taxes, investments)
    gross_debits = sum(float(t["debit"]) for t in debits)
    excluded_debit_cats = {
        "SELF_TRANSFER_DR", "LOAN_EMI", "INTEREST_EXPENSE", "TAX_GST",
        "INVESTMENT_OUTFLOW", "BOUNCE_PENALTY", "LOAN_DISBURSEMENT",
        "DEPOSIT_RETURN", "RELATED_PARTY_DR", "REVERSAL_DR", "REVERSED_DEBIT", "PERSONAL_LOAN_DR",
        "PASS_THROUGH_DR",
    }

    op_debits = [
        t for t in debits
        if not t.get("is_contra")
        and t.get("category") not in excluded_debit_cats
        and t.get("is_operating_expense", True)
    ]
    # Payments the unverified cash itself paid for (cash deposited, then paid
    # on to the same party) leave with it: dropping the cash but keeping what
    # it funded would invent a deficit. Both sides are reported together as
    # the unverified cash cycle.
    cash_funded = _cash_funded_payments(annotated, op_debits)
    op_debits = [t for t in op_debits if id(t) not in cash_funded]
    for t in annotated:
        if id(t) in cash_funded:
            t["cash_funded"] = True
            t["purpose"] = "Paid from unverified cash (set aside with it)"
    tot_cash_funded = sum(float(t["debit"]) for t in annotated if id(t) in cash_funded)
    total_operating_expenses = sum(float(t["debit"]) for t in op_debits)
    monthly_operating_expenses = total_operating_expenses / num_months

    # Month by month on the same basis as the headline figures: eligible
    # receipts less operating expenses less the EMI and interest paid that month
    by_month = defaultdict(lambda: {"eligible_receipts": 0.0, "operating_expenses": 0.0, "debt_service": 0.0})
    for t in salary_inflows + business_inflows + rental_inflows + interest_inflows + investment_inflows + other_recurring:
        if t.get("txn_date"):
            by_month[t["txn_date"].strftime("%Y-%m")]["eligible_receipts"] += float(t["credit"])
    for t in op_debits:
        if t.get("txn_date"):
            by_month[t["txn_date"].strftime("%Y-%m")]["operating_expenses"] += float(t["debit"])
    for t in debits:
        if t.get("txn_date") and t.get("category") in ("LOAN_EMI", "INTEREST_EXPENSE"):
            by_month[t["txn_date"].strftime("%Y-%m")]["debt_service"] += float(t["debit"])
    for m in months_seen:
        by_month[m]
    monthly_operating = []
    for m in sorted(by_month):
        v = by_month[m]
        net = v["eligible_receipts"] - v["operating_expenses"] - v["debt_service"]
        monthly_operating.append({"month": m, **{k: round(x, 2) for k, x in v.items()},
                                  "operating_net": round(net, 2),
                                  "operating_status": "SURPLUS" if net >= 0 else "DEFICIT"})
    total_excluded_debits = gross_debits - total_operating_expenses
    estimated_monthly_operating_surplus = monthly_eligible_income - monthly_operating_expenses

    # Track excluded debits breakdown
    debit_exclusions_map = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for t in debits:
        c = t.get("category", "")
        amt = float(t["debit"])
        if id(t) in cash_funded:
            debit_exclusions_map["Payments Funded by Unverified Cash"]["amount"] += amt
            debit_exclusions_map["Payments Funded by Unverified Cash"]["count"] += 1
        elif t.get("is_contra") or c in excluded_debit_cats or not t.get("is_operating_expense", True):
            label = {
                "SELF_TRANSFER_DR": "Self / Contra Transfers (DR)",
                "LOAN_EMI": "Loan EMI Repayments",
                "INTEREST_EXPENSE": "Financing & OD Interest",
                "TAX_GST": "Direct / Indirect Taxes (GST / IT)",
                "INVESTMENT_OUTFLOW": "Investments & Sweeps",
                "CREDIT_CARD_PAYMENT": "Credit Card Bill Repayments",
                "BOUNCE_PENALTY": "Cheque / ECS Bounce Charges",
                "LOAN_DISBURSEMENT": "Loan Outflow Reversals",
                "DEPOSIT_RETURN": "Deposited Cheques Returned Unpaid",
                "REVERSAL_DR": "Bank Reversals of Wrong Credits",
                "PERSONAL_LOAN_DR": "Money Lent to Individuals",
                "REVERSED_DEBIT": "Debits Later Reversed",
                "PASS_THROUGH_DR": "Pass-Through Payments (paid back out)",
                "RELATED_PARTY_DR": "Possible Related-Party Payments",
            }.get(c, "Other Non-Operating Debits")
            debit_exclusions_map[label]["amount"] += amt
            debit_exclusions_map[label]["count"] += 1

    excluded_debit_categories = [
        {"category": k, "amount": round(v["amount"], 2), "count": v["count"]}
        for k, v in debit_exclusions_map.items()
    ]

    # Concentration Analysis
    payer_credits = defaultdict(float)
    for t in (salary_inflows + business_inflows + other_recurring):
        cp = t.get("counterparty") or "Unknown"
        if cp in ("Unknown", "Cash"):
            continue        # unnamed cheques / cash are not one payer
        payer_credits[cp] += float(t["credit"])

    sorted_payers = sorted(payer_credits.items(), key=lambda x: x[1], reverse=True)
    top1_payer = sorted_payers[0][0] if sorted_payers else "-"
    top1_share = (sorted_payers[0][1] / total_eligible_income * 100) if (sorted_payers and total_eligible_income > 0) else 0.0

    income_metric_label = (
        "Average Monthly Eligible Business Receipts"
        if is_business
        else "Eligible Monthly Income"
    )

    excluded_categories = [
        {"category": "Self / Contra Transfers", "amount": round(tot_self, 2), "count": len(self_transfers), "reason": "Internal liquidity moving between borrower's own accounts"},
        {"category": "Loan Disbursements", "amount": round(tot_loans, 2), "count": len(loan_disbursements), "reason": "Debt liabilities, not earned operating income"},
        {"category": "Refunds & Reversals", "amount": round(tot_refunds, 2), "count": len(tax_refunds + refund_reversals), "reason": "Pass-through debit reversals and tax refunds"},
        {"category": "Capital Infusion / Large Spikes", "amount": round(tot_capital, 2), "count": len(capital_infusions), "reason": "Non-recurring equity, owner capital, or anomalous spikes"},
    ]
    if related_inflows:
        excluded_categories.append({
            "category": "Possible Related-Party Inflows", "amount": round(tot_related, 2),
            "count": len(related_inflows),
            "reason": "Party shares the holder's name (sister firm / family); neither own money nor arm's-length revenue"})
    if bank_funded:
        excluded_categories.append({
            "category": "Inflows Paid in by a Bank (Review)", "amount": round(tot_bank, 2), "count": len(bank_funded),
            "reason": "A bank as the payer is a loan, OD or routed remittance until shown to be a customer payment"})
    if pass_through:
        excluded_categories.append({
            "category": "Pass-Through Receipts", "amount": round(tot_pass, 2), "count": len(pass_through),
            "reason": "Same party's money received and paid back out within 7 days; not earned income"})
    if personal_credits:
        excluded_categories.append({
            "category": "Pending Review: Credits from Individuals (Purpose Unknown)", "amount": round(tot_personal, 2),
            "count": len(personal_credits),
            "reason": "The statement shows who paid, not why (client fee, repayment, family money); not counted "
                      "until reviewed. Regular one-way or same-amount monthly payers are already counted"})
    if non_operating:
        excluded_categories.append({
            "category": "Non-Operating Inflows", "amount": round(tot_non_op, 2), "count": len(non_operating),
            "reason": "Insurance payouts and deposits that were later returned unpaid"})
    if unclassified_inflows:
        excluded_categories.append({
            "category": "Unclassified Inflows", "amount": round(tot_unclassified, 2),
            "count": len(unclassified_inflows),
            "reason": "No identifiable party and no rule match; not counted as income until explained"})
    if cash_deposits:
        excluded_categories.append({
            "category": "Cash Deposits (Source Unverified)",
            "amount": round(tot_cash_dep, 2),
            "count": len(cash_deposits),
            "reason": "A statement shows cash came in, not where from (sales, owner's money, cash loan); reported separately, not counted as income"
        })

    return {
        "is_business": is_business,
        "cash_collection_model": cash_collection_model,
        "income_meaningful": income_meaningful,
        "monthly_operating": monthly_operating,
        "income_metric_label": income_metric_label,
        "observed_monthly_eligible_receipts": round(observed_monthly_eligible, 2),
        "underwriting_income_baseline": round(monthly_eligible_income, 2),
        "underwriting_baseline_type": underwriting_baseline_type,
        "median_monthly_salary": round(median_salary, 2),
        "monthly_eligible_income": round(monthly_eligible_income, 2),
        "total_eligible_income": round(total_eligible_income, 2),
        "total_excluded_inflows": round(total_excluded, 2),
        "gross_credits": round(gross_credits, 2),
        # credits from individuals awaiting review: not in income until shown to be
        "pending_review_personal_credits": round(tot_personal, 2),
        "pending_review_personal_count": len(personal_credits),
        "monthly_income_if_review_accepted": round((total_eligible_income + tot_personal) / num_months, 2),
        "total_cash_deposits": round(tot_cash_dep, 2),
        "monthly_cash_deposits": round(tot_cash_dep / num_months, 2),
        # cash cannot be verified from a statement, so all of it is unverified
        "verified_cash_deposits": 0.0,
        "unverified_cash_deposits": round(tot_cash_dep, 2),
        "cash_share_of_inflows_pct": round(tot_cash_dep / gross_credits * 100, 2) if gross_credits else 0.0,
        "cash_funded_payments": round(tot_cash_funded, 2),
        "monthly_cash_funded_payments": round(tot_cash_funded / num_months, 2),
        # share of all operating payments that were set aside with the cash: when
        # it is most of them, a margin on what is left describes the set-aside
        "cash_funded_share_of_expenses_pct": round(
            tot_cash_funded / (tot_cash_funded + total_operating_expenses) * 100, 2)
            if (tot_cash_funded + total_operating_expenses) else 0.0,
        "cash_funded_payments_count": len(cash_funded),
        # what the cash leaves after the payments it funded, per month: the
        # operating cash the account would show if the cash were income
        "monthly_unverified_cash_net": round((tot_cash_dep - tot_cash_funded) / num_months, 2),
        "verified_business_receipts": round(tot_biz, 2),
        "months_count": round(num_months, 2),
        "calendar_months_with_activity": len(months_seen),
        "total_unclassified_inflows": round(tot_unclassified, 2),
        "unclassified_inflow_share_pct": round(tot_unclassified / gross_credits * 100, 2) if gross_credits else 0.0,
        "gross_debits": round(gross_debits, 2),
        "total_operating_expenses": round(total_operating_expenses, 2),
        "monthly_operating_expenses": round(monthly_operating_expenses, 2),
        "total_excluded_debits": round(total_excluded_debits, 2),
        "estimated_monthly_operating_surplus": round(estimated_monthly_operating_surplus, 2),
        "eligible_categories": [
            {"category": "Salary / Payroll", "amount": round(tot_salary, 2), "count": len(salary_inflows)},
            {"category": "Business Trade Receipts", "amount": round(tot_biz, 2), "count": len(business_inflows)},
            {"category": "Rental Income", "amount": round(tot_rent, 2), "count": len(rental_inflows)},
            {"category": "Interest Income", "amount": round(tot_int, 2), "count": len(interest_inflows)},
            {"category": "Investment Returns", "amount": round(tot_inv, 2), "count": len(investment_inflows)},
            {"category": "Other Operating Inflows", "amount": round(tot_other, 2), "count": len(other_recurring)},
        ],
        "excluded_categories": excluded_categories,
        "excluded_debit_categories": excluded_debit_categories,
        "concentration": {
            "top1_payer": top1_payer,
            "top1_share_pct": round(top1_share, 2),
            "payer_count": len(sorted_payers),
        },
    }
