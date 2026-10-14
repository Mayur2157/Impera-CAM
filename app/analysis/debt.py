"""Module 4: Debt & Obligation Analysis.

Detects term loan EMIs, credit card repayments, interest expenses, loan disbursals,
and computes mathematically sound FOIR (Retail & Business) and DSCR (Debt Service Coverage Ratio).
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from .classifier import classify_all_transactions
from .narration_rules import LOAN_ACCOUNT_RX, LOAN_CLOSED_RX, match_lender


ACTIVE_WINDOW_DAYS = 45


def _loan_key(t: dict) -> tuple[str, str]:
    """(lender, stable id). One id is one loan however the lender is spelled.

    Loan account numbers are stable. Mandate ids are only stable in the
    old 'ACH Debit/<lender>/<umrn>' and 'ECS/<id>/<lender>' layouts; BoB's
    'ACHDR<n>/…' prints a new number every month, so those fall back to the
    lender and are merged by amount below."""
    narr = t.get("narration") or ""
    lender = match_lender(narr) or t.get("counterparty") or "Unknown Lender"
    m = LOAN_ACCOUNT_RX.search(narr)
    if m:
        return (match_lender(narr) or f"Loan A/c {m.group(1)}", m.group(1))
    m = re.search(r"ACH\s*DEBIT/[^/]+/(\d{6,})", narr, re.I) or re.search(r"\bECS/(\d{6,})/", narr, re.I)
    if m:
        return (lender, m.group(1))
    return (lender, "")


def _group_loans(emi_txns: list[dict]) -> dict[tuple, list]:
    groups: dict[tuple, list] = defaultdict(list)
    loan_accounts = set()
    for t in emi_txns:
        key = _loan_key(t)
        groups[key].append(t)
        if LOAN_ACCOUNT_RX.search(t.get("narration") or ""):
            loan_accounts.add(key[1])

    # Same lender, no stable id, same instalment (±5%) → the same loan
    # (BoB Hero 'ACH Debit/…/26856156' then 'ACHDR…/HERO FINCORP LTD/…').
    def typical(ts):
        return statistics.median(float(x["debit"]) for x in ts)
    for key in [k for k in groups if not k[1]]:
        if key not in groups:
            continue
        for other in list(groups):
            if other == key or other[0] != key[0] or other not in groups:
                continue
            a, b = typical(groups[key]), typical(groups[other])
            if abs(a - b) <= 0.05 * max(a, b):
                groups[other].extend(groups.pop(key))
                break

    out: dict[tuple, list] = {}
    for key, ts in groups.items():
        ts.sort(key=lambda x: x.get("txn_date") or date.min)
        if key[1] and key[1] in loan_accounts:
            # a loan account is definitive: same-month pieces are one EMI paid in parts
            out[key] = ts
            continue
        if key[1]:
            bands = _split_same_days(ts)
        else:
            bands = _cluster_by_amount(ts)
        for n, b in enumerate(bands):
            out[(key[0], key[1] + (f"#{n + 1}" if len(bands) > 1 else ""))] = b
    return out


def _has_collection_day(pay_days: list[date], window: int = 3) -> bool:
    """3+ payments whose days of the month agree within ±window days."""
    if len(pay_days) < 3:
        return False
    doms = [d.day for d in pay_days]
    typical = statistics.median(doms)
    return statistics.median(abs(x - typical) for x in doms) <= window


def _on_collection_day(day: date, pay_days: list[date], window: int = 3) -> bool:
    """True when `day` is within ±window days of the day of the month this loan
    is regularly collected on. Needs 3+ payments whose days of the month agree."""
    if not _has_collection_day(pay_days, window):
        return False            # no steady collection day
    typical = statistics.median(d.day for d in pay_days)
    diff = abs(day.day - typical)
    return min(diff, 31 - diff) <= window


def _split_same_days(ts: list[dict]) -> list[list]:
    """Two different instalments under one mandate id within 3 days are two
    loans (United 'ECS/4009033/HDFC BANK LIMITED' ₹17,474 and ₹19,402)."""
    bands: list[list] = []
    for x in ts:
        amt = float(x["debit"])
        near = [b for b in bands if any(
            y.get("txn_date") and x.get("txn_date") and abs((x["txn_date"] - y["txn_date"]).days) <= 3
            and abs(float(y["debit"]) - amt) > 0.05 * amt for y in b)]
        home = next((b for b in bands if b not in near), None)
        if home is None:
            bands.append([x])
        else:
            home.append(x)
    return bands


def _cluster_by_amount(ts: list[dict]) -> list[list]:
    """No id: one lender's debits split by instalment (±5%). A one-off amount
    is a part-payment of the main loan, not a loan of its own."""
    clusters: list[list] = []
    for x in sorted(ts, key=lambda x: float(x["debit"])):
        amt = float(x["debit"])
        if clusters and abs(float(clusters[-1][0]["debit"]) - amt) <= 0.05 * amt:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    # a separate loan recurs: its instalment appears in 3+ different months
    def months(c):
        return len({x["txn_date"].strftime("%Y-%m") for x in c if x.get("txn_date")})
    main = [c for c in clusters if months(c) >= 3]
    if not main:
        return [ts]
    biggest = max(main, key=len)
    for c in clusters:
        if c not in main:
            biggest.extend(c)
    for c in main:
        c.sort(key=lambda x: x.get("txn_date") or date.min)
    return main


def _recurring_unexplained(annotated: list[dict]) -> list[dict]:
    """Debits to one party, same amount (±5%), about monthly, 3+ times, that no
    rule explained as a loan. Surfaced for review rather than guessed at."""
    by_cp = defaultdict(list)
    for t in annotated:
        if t.get("debit") and t.get("txn_date") and t.get("category") in ("BUSINESS_EXPENSE", "UNCLASSIFIED_DR", "BILL_PAYMENT"):
            by_cp[t.get("counterparty") or ""].append(t)
    hits = []
    for cp, ts in by_cp.items():
        if not cp or cp in ("Unknown", "Cash", "Bank"):
            continue
        ts.sort(key=lambda x: x["txn_date"])
        for i in range(len(ts)):
            run = [ts[i]]
            for x in ts[i + 1:]:
                gap = (x["txn_date"] - run[-1]["txn_date"]).days
                if 25 <= gap <= 35 and abs(float(x["debit"]) - float(run[0]["debit"])) <= 0.05 * float(run[0]["debit"]):
                    run.append(x)
            if len(run) >= 3:
                hits.append({"counterparty": cp, "occurrences": len(run),
                             "amount": round(float(run[0]["debit"]), 2),
                             "first_date": run[0]["txn_date"].strftime("%d-%b-%Y")})
                break
    return hits


def analyze_debt(
    txns: list[dict],
    income_data: dict,
    eligible_income_data: dict | None = None,
    customer_name: str = "",
    statement_end: date | None = None,
    months_covered: float | None = None,
) -> dict[str, Any]:
    if not txns or "category" not in txns[0]:
        annotated = classify_all_transactions(txns, customer_name)
    else:
        annotated = txns

    debits = [t for t in annotated if t.get("debit") and t["debit"] > 0]
    credits = [t for t in annotated if t.get("credit") and t["credit"] > 0]

    # 1. Filter Debt Categories
    emi_txns = [t for t in debits if t.get("category") == "LOAN_EMI"]
    cc_txns = [t for t in debits if t.get("category") == "CREDIT_CARD_PAYMENT"]
    interest_txns = [t for t in debits if t.get("category") == "INTEREST_EXPENSE"]
    loan_disbursals = [t for t in credits if t.get("category") == "LOAN_DISBURSEMENT"]

    # 2. Group EMIs into loans (see _group_loans) and keep only live ones
    period_end = max((t["txn_date"] for t in annotated if t.get("txn_date")), default=None)
    if statement_end and period_end:
        period_end = max(period_end, statement_end)
    own_bounces = [t for t in annotated if t.get("bounce_side") == "OWN" and t.get("txn_date")]
    loan_summary = []
    total_monthly_emi = 0.0
    for key, t_list in _group_loans(emi_txns).items():
        t_list.sort(key=lambda x: x.get("txn_date") or date.min)
        amts = [float(x["debit"]) for x in t_list]
        by_month = defaultdict(float)
        for x in t_list:
            if x.get("txn_date"):
                by_month[x["txn_date"].strftime("%Y-%m")] += float(x["debit"])
        # EMI = what is paid in a month; fragments (₹373.66 + ₹6,414.34) add up
        monthly = statistics.median(by_month.values()) if by_month else sum(amts)
        last = t_list[-1].get("txn_date")
        closures = [x["txn_date"] for x in annotated
                    if LOAN_CLOSED_RX.search(x.get("narration") or "")
                    and key[1].split("#")[0] and key[1].split("#")[0] in (x.get("narration") or "")
                    and x.get("txn_date") and last and x["txn_date"] >= last]
        closed = bool(closures)
        active = bool(last and period_end and (period_end - last).days <= ACTIVE_WINDOW_DAYS and not closed)
        if active:
            total_monthly_emi += monthly
        pay_days = [x["txn_date"] for x in t_list if x.get("txn_date")]
        loan_summary.append({
            "lender": key[0],
            "loan_reference": key[1] or "-",
            "status": "ACTIVE" if active else ("CLOSED" if closed else "NOT PAID IN LAST 45 DAYS"),
            "installments_detected": len(t_list),
            "typical_emi_amount": round(monthly, 2),
            "total_paid": round(sum(amts), 2),
            "first_paid_date": pay_days[0].strftime("%d-%b-%Y") if pay_days else "-",
            "last_paid_date": pay_days[-1].strftime("%d-%b-%Y") if pay_days else "-",
            "linked_bounces": 0,
            "_pay_days": pay_days,
            "_rows": [id(x) for x in t_list],
            "_closed_on": min(closures) if closures else None,
        })

    # A return is tied to a loan only on evidence, and only when that evidence
    # points to one loan; anything weaker is UNKNOWN, with the loans it could
    # have been listed. Evidence, strongest first:
    #   1. the return quotes the loan's account / mandate number;
    #   2. it names the lender, and that lender has one loan live then;
    #   3. it falls on a loan's steady collection day (3+ payments) and that
    #      is the only loan live then.
    # 'Live' = from one cycle before the first payment to one cycle after the
    # last: a loan last paid in Sep 2019 cannot explain a Dec 2019 return.
    # A loan closed before the return cannot have bounced at all.
    dup_lenders = {l["lender"] for l in loan_summary
                   if sum(1 for m in loan_summary if m["lender"] == l["lender"]) > 1}

    def _loan_name(l):
        return f"{l['lender']} ({l['loan_reference']})" if l["lender"] in dup_lenders else l["lender"]

    cycle = timedelta(days=35)
    pos = {id(t): i for i, t in enumerate(annotated)}
    unlinked_live = 0
    for b in own_bounces:
        narr = b.get("narration") or ""
        day = b["txn_date"]
        open_loans = [l for l in loan_summary if not (l["_closed_on"] and l["_closed_on"] < day)]
        live = [l for l in open_loans if l["_pay_days"]
                and l["_pay_days"][0] - cycle <= day <= l["_pay_days"][-1] + cycle]
        # a loan whose instalment went through in the 5 days before the
        # return (posted ahead of it) was already paid for this cycle
        live = [l for l in live if not any(
            pos[r] < pos[id(b)] and 0 <= (day - annotated[pos[r]]["txn_date"]).days <= 5
            for r in l["_rows"] if annotated[pos[r]].get("txn_date"))]
        narr_digits = set(re.findall(r"\d{5,}", narr))
        loan, basis, evidenced, candidates = None, None, False, []
        by_ref = [l for l in open_loans
                  if l["loan_reference"].split("#")[0] and l["loan_reference"].split("#")[0] in narr_digits]
        named = match_lender(narr)
        if len(by_ref) == 1:
            loan, basis = by_ref[0], "loan / mandate number quoted in the return"
        elif named:
            same = [l for l in live if l["lender"] == named] or \
                   [l for l in open_loans if l["lender"] == named]
            if len(same) == 1:
                loan, basis = same[0], "lender named in the return; its only loan then"
            candidates = same
            evidenced = bool(same)
        else:
            # a live loan is ruled out only by a steady collection day that
            # is not this one; a loan paid on irregular days stays possible
            due = [l for l in live if _on_collection_day(day, l["_pay_days"])
                   or not _has_collection_day(l["_pay_days"])]
            if len(due) == 1 and _on_collection_day(day, due[0]["_pay_days"]):
                loan, basis = due[0], "on its collection day; no other loan due then"
            # off every collection day it can still be an instalment presented
            # again, so all live loans stay possible
            candidates = due or live
            evidenced = any(_on_collection_day(day, l["_pay_days"]) for l in due)
        lenders = {l["lender"] for l in candidates}
        if loan is not None:
            b["_linked_loan"] = _loan_name(loan)
            b["_loan_link_basis"] = basis
            loan["linked_bounces"] += 1
        elif evidenced and len(lenders) == 1:
            # the loan is ambiguous but the lender is not: every loan due then
            # is with one lender (Cosmos Thane: IDFC #2 or #3 on IDFC's 2nd).
            # Off every collection day this is not claimed (any cheque could bounce)
            lender = lenders.pop()
            b["_linked_loan"] = f"{lender} (loan not identified)"
            b["_loan_link_basis"] = ("lender named in the return" if named else "on the lender's collection day") + \
                f"; every loan due then is with {lender}: " + ", ".join(_loan_name(l) for l in candidates)
        else:
            b["_linked_loan"] = "UNKNOWN"
            b["_loan_link_basis"] = ("possible: " + ", ".join(_loan_name(l) for l in candidates)
                                     if candidates else "no loan was being repaid then")
            if live:
                unlinked_live += 1
    for l in loan_summary:
        l.pop("_pay_days", None)
        l.pop("_closed_on", None)
        l.pop("_rows", None)

    total_cc_repayments = sum(float(t["debit"]) for t in cc_txns)
    total_interest_paid = sum(float(t["debit"]) for t in interest_txns)
    total_emi_paid = sum(float(t["debit"]) for t in emi_txns)

    # 3. Disbursals
    disbursal_summary = []
    for t in loan_disbursals:
        disbursal_summary.append({
            "date": t["txn_date"].strftime("%d-%b-%Y") if t.get("txn_date") else "-",
            "amount": round(float(t["credit"]), 2),
            "source": t.get("counterparty") or "Fintech / Bank",
            "narration": (t.get("narration") or "")[:60],
        })

    # 4. Underwriting Ratios: Unified Cash Flow Waterfall
    # Eligible Operating Inflows vs Outflows
    months_span = months_covered or max(1, len(income_data.get("monthly_breakdown", [])) or 1)
    if eligible_income_data:
        tot_op_inflows = eligible_income_data.get("total_eligible_income")
        if tot_op_inflows is None:
            tot_op_inflows = eligible_income_data.get("monthly_eligible_income", 0.0) * months_span
        tot_op_debits = eligible_income_data.get("total_operating_expenses")
        if tot_op_debits is None:
            tot_op_debits = eligible_income_data.get("monthly_operating_expenses", 0.0) * months_span
        if tot_op_debits == 0.0:
            tot_op_debits = sum(float(t["debit"]) for t in annotated if t.get("debit") and t.get("category") not in ("LOAN_EMI", "LOAN_DISBURSAL", "INTEREST_PAID", "FINANCE_CHARGES"))

        monthly_eligible = eligible_income_data.get("monthly_eligible_income")
        if monthly_eligible is None or monthly_eligible == 0.0:
            monthly_eligible = tot_op_inflows / months_span

        monthly_op_exp = eligible_income_data.get("monthly_operating_expenses")
        if monthly_op_exp is None or monthly_op_exp == 0.0:
            monthly_op_exp = tot_op_debits / months_span
    else:
        tot_op_inflows = sum(float(t["credit"]) for t in annotated if t.get("is_revenue"))
        tot_op_debits = sum(float(t["debit"]) for t in annotated if t.get("is_operating_expense"))
        monthly_eligible = tot_op_inflows / months_span
        monthly_op_exp = tot_op_debits / months_span

    # Operating Cash Available (CADS before debt service)
    # Since Operating Expenses already excludes Interest and EMIs:
    # Operating Cash Available = Revenue - Operating Expenses
    operating_cash_available = tot_op_inflows - tot_op_debits
    monthly_operating_cash = monthly_eligible - monthly_op_exp

    # Debt service = what was actually paid toward debt in the statement
    # period: every EMI / loan repayment (including loans that closed or
    # stopped before the end), plus OD / loan interest, per month covered.
    # Loan money received, own transfers and refunds are not debt service.
    # Card bills pay for spending, so they sit in operating expenses instead.
    # The current EMI on active loans (`total_monthly_emi`) is a forward-looking
    # figure, reported beside it but not used in the ratios.
    monthly_interest = total_interest_paid / months_span
    monthly_emi_paid = total_emi_paid / months_span
    monthly_card = total_cc_repayments / months_span
    monthly_debt_service = monthly_emi_paid + monthly_interest
    total_debt_service = total_emi_paid + total_interest_paid
    period_start = (period_end - timedelta(days=round(months_span * 30.4))) if period_end else None
    new_loan_in_period = bool(period_start) and any(
        l["status"] == "ACTIVE" and l["first_paid_date"] != "-"
        and datetime.strptime(l["first_paid_date"], "%d-%b-%Y").date() > period_start + timedelta(days=35)
        for l in loan_summary)

    # retail logic (FOIR, no DSCR) for any individual's account, not only salaried ones
    is_salaried = income_data.get("is_salaried", False) or (
        eligible_income_data is not None and not eligible_income_data.get("is_business", True))

    if is_salaried:
        debt_ratio_label = "Fixed Obligation to Income Ratio (FOIR)"
        foir_type = "RETAIL_FOIR"
        # every fixed monthly obligation: EMIs, card repayments, interest
        actual_foir = (monthly_debt_service / monthly_eligible * 100.0) if monthly_eligible > 0 else (0.0 if monthly_debt_service == 0 else 100.0)
        if actual_foir <= 35.0:
            foir_rating = "Band: <=35%"
        elif actual_foir <= 50.0:
            foir_rating = "Band: 35-50%"
        else:
            foir_rating = "Band: >50%"
        dscr = None
        raw_dscr = None
        dscr_assessment = "NOT_APPLICABLE_RETAIL"
        dscr_display = "N/A (Individual / Retail Account)"
        debt_burden_pct = round(actual_foir, 2)
        op_cash_coverage_ratio = None
        op_cash_coverage_status = "RETAIL_ACCOUNT"
    else:
        # Commercial / Business Account:
        # Business Debt Service / Revenue Ratio = (EMI + OD Interest + Financing Charges) / Revenue * 100
        debt_ratio_label = "Business Debt Service / Revenue Ratio"
        foir_type = "BUSINESS_DEBT_TO_REVENUE"
        actual_foir = (monthly_debt_service / monthly_eligible * 100.0) if monthly_eligible > 0 else (0.0 if monthly_debt_service == 0 else 100.0)
        if actual_foir <= 30.0:
            foir_rating = "Band: <30%"
        elif actual_foir <= 50.0:
            foir_rating = "Band: 30-50%"
        else:
            foir_rating = "Band: >50%"

        debt_burden_pct = round(actual_foir, 2)

        # DSCR & Operating Cash Coverage use the EXACT same unified waterfall:
        # Coverage = Operating Cash Available / Total Debt Service
        if total_debt_service > 0:
            raw_cov = (monthly_operating_cash / monthly_debt_service) if monthly_debt_service > 0 else (operating_cash_available / total_debt_service)
            raw_dscr = round(raw_cov, 2)
            op_cash_coverage_ratio = raw_dscr

            if monthly_operating_cash < 0:
                dscr = None
                dscr_assessment = "Negative operating cash flow"
                dscr_display = "N/M"
                op_cash_coverage_status = "DEFICIT (Operating Inflows Insufficient)"
            else:
                dscr = raw_dscr
                if dscr >= 1.5:
                    dscr_assessment = "Above 1.5x"
                    op_cash_coverage_status = "Above 1.5x"
                elif dscr >= 1.2:
                    dscr_assessment = "1.2x - 1.5x"
                    op_cash_coverage_status = "1.2x - 1.5x"
                elif dscr >= 1.0:
                    dscr_assessment = "1.0x - 1.2x"
                    op_cash_coverage_status = "1.0x - 1.2x"
                else:
                    dscr_assessment = "Below 1.0x (Deficit)"
                    op_cash_coverage_status = "Below 1.0x (Deficit)"
                dscr_display = f"{dscr:.2f}x ({dscr_assessment})"
        else:
            # Debt free
            raw_dscr = None
            dscr = None
            dscr_assessment = "N/A — No Debt Service"
            dscr_display = "N/A — No Debt Service (Debt Burden: 0%)"
            op_cash_coverage_ratio = None
            op_cash_coverage_status = "DEBT_FREE"

    # The same coverage if the unverified cash (less what it paid for) were
    # income: shown beside the verified DSCR, never used in the score
    dscr_incl_cash = None
    cash_net = (eligible_income_data or {}).get("monthly_unverified_cash_net") or 0.0
    if dscr_assessment != "NOT_APPLICABLE_RETAIL" and monthly_debt_service > 0 and cash_net > 0:
        dscr_incl_cash = round((monthly_operating_cash + cash_net) / monthly_debt_service, 2)

    # Own-side returns that fall on a loan's payment dates (±5 days)
    bounce_on_loans = sum(1 for t in own_bounces if t.get("_linked_loan") not in (None, "UNKNOWN"))

    # Say only what the statement shows: nothing to test, too little to call
    # regular, or a real history
    if not loan_summary:
        loan_regularity = "N/A — No loan repayments detected"
    elif bounce_on_loans:
        loan_regularity = f"{bounce_on_loans} EMI BOUNCE(S) DETECTED" + (
            f"; {unlinked_live} more return(s) with loan link UNKNOWN" if unlinked_live else "")
    elif unlinked_live:
        loan_regularity = (f"UNCONFIRMED — {unlinked_live} own-payment return(s) while loans were "
                           f"being repaid; loan link UNKNOWN")
    elif max(l["installments_detected"] for l in loan_summary) < 3:
        loan_regularity = "Limited history — no bounce observed"
    else:
        loan_regularity = "REGULAR — 0 EMI Bounces"

    # No meaningful income: debt-to-income is not a number worth printing
    if eligible_income_data and eligible_income_data.get("income_meaningful") is False:
        actual_foir = None
        debt_burden_pct = None
        foir_rating = "N/M (no meaningful eligible income)"

    return {
        "active_loans_count": sum(1 for l in loan_summary if l["status"] == "ACTIVE"),
        "loans_detected_count": len(loan_summary),
        "recurring_debits_for_review": _recurring_unexplained(annotated),
        "total_monthly_emi_obligation": round(total_monthly_emi, 2),     # current EMI on active loans
        "monthly_emi_paid": round(monthly_emi_paid, 2),                    # EMIs actually paid, per month
        # a loan that started during the period: its EMI now runs every month,
        # so the period's average understates it. A short statement holding one
        # instalment of an old loan is not this case.
        "forward_emi_exceeds_paid": bool(total_monthly_emi > 1.25 * monthly_emi_paid and new_loan_in_period),
        "total_monthly_interest_obligation": round(monthly_interest, 2),
        "total_monthly_debt_service": round(monthly_debt_service, 2),
        "total_emi_paid_in_period": round(total_emi_paid, 2),
        "credit_card_repayments_paid": round(total_cc_repayments, 2),
        "total_monthly_card_repayments": round(monthly_card, 2),
        "credit_card_payments_count": len(cc_txns),
        "interest_expenses_paid": round(total_interest_paid, 2),
        "total_debt_service_in_period": round(total_debt_service, 2),
        "loan_disbursals_count": len(disbursal_summary),
        "total_loan_disbursals": round(sum(d["amount"] for d in disbursal_summary), 2),
        "debt_ratio_label": debt_ratio_label,
        "foir_percentage": round(actual_foir, 2) if actual_foir is not None else None,
        "foir_calculation_type": foir_type,
        "foir_risk_category": foir_rating,
        "operating_cash_coverage_ratio": op_cash_coverage_ratio,
        "operating_cash_coverage_status": op_cash_coverage_status,
        "debt_burden_percentage": debt_burden_pct,
        "cads": round(operating_cash_available, 2),
        "monthly_operating_cash_available": round(monthly_operating_cash, 2),
        "raw_dscr": round(raw_dscr, 2) if raw_dscr is not None else None,
        "dscr": round(dscr, 2) if dscr is not None else None,
        "dscr_assessment": dscr_assessment,
        "dscr_display": dscr_display,
        "dscr_incl_unverified_cash": dscr_incl_cash,
        "loan_emi_bounces_count": bounce_on_loans,
        "unlinked_returns_while_loans_live": unlinked_live,
        "emi_regularity": loan_regularity,
        "loans": loan_summary,
        "disbursals": disbursal_summary,
    }
