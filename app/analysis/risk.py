"""Module 8: Risk Analysis & Bounces.

Detects payment/ECS bounces, bank penalties, window dressing (EOM balance inflation),
overdraft stress, and rapid external pass-through fund transfers (excluding self transfers).
"""
from __future__ import annotations

import re
from datetime import timedelta
import statistics
from typing import Any

from .classifier import classify_all_transactions
from .narration_rules import same_party


_FEE_TYPES = [
    (re.compile(r"MIN(?:IMUM)?\.?\s*BAL|NON\s*MAINT", re.I), "Minimum Balance Fee"),
    (re.compile(r"RTN|RETURN|REJECT|HRET|RT-CHG|DISHON|BOUNCE", re.I), "Return Charge"),
    (re.compile(r"LATE|OVERDUE", re.I), "Late Payment Fee"),
    (re.compile(r"PENAL", re.I), "Penal Charge"),
]


def _fee_type(narration: str) -> str:
    """Name a fee by what the bank says it is ('CHRG: MINIMUM BAL' is a
    minimum-balance fee, not a generic 'penalty')."""
    for rx, label in _FEE_TYPES:
        if rx.search(narration or ""):
            return label
    return "Bank Fee"


def _bounced_payment(txns: list[dict], charge: dict, days: int = 35):
    """Amount of the payment a return charge was for, when the statement shows
    it: a debit within `days` quoting the same cheque / instrument number as
    the charge (usually the cheque presented again and paid). Otherwise
    'UNKNOWN' — the charge is never reported as the bounced amount."""
    narr = charge.get("narration") or ""
    inst = set(re.findall(r"(?<!\d)(\d{3,8})(?!\d)", narr))
    day = charge.get("txn_date")
    if not inst or not day:
        return "UNKNOWN"
    for t in txns:
        if t is charge or not t.get("debit") or t.get("bounce_side") or not t.get("txn_date"):
            continue
        if abs((t["txn_date"] - day).days) > days:
            continue
        ref = (t.get("reference") or "").strip().lstrip("0")
        if any(ref == i.lstrip("0") for i in inst):
            return round(float(t["debit"]), 2)
    return "UNKNOWN"


def analyze_risk(
    txns: list[dict],
    health_data: dict | None = None,
    customer_name: str = "",
) -> dict[str, Any]:
    if not txns or "category" not in txns[0]:
        annotated = classify_all_transactions(txns, customer_name)
    else:
        annotated = txns

    health_data = health_data or {}
    bounces = []
    penalties = []
    large_txns = []

    amounts = []
    total_inflow = 0.0
    total_outflow = 0.0

    for t in annotated:
        c = float(t["credit"]) if t.get("credit") else 0.0
        d = float(t["debit"]) if t.get("debit") else 0.0
        amounts.append(c + d)
        total_inflow += c
        total_outflow += d

    mean_amt = statistics.mean(amounts) if amounts else 0.0
    large_threshold = max(50000.0, mean_amt * 3.5)

    neg_balances = []

    for t in annotated:
        narr = t.get("narration") or ""
        crd = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        bal = float(t["balance"]) if t.get("balance") is not None else None
        d_str = t["txn_date"].strftime("%d-%b-%Y") if t.get("txn_date") else "-"
        cat = t.get("category", "")

        if bal is not None and bal < 0:
            neg_balances.append(bal)

        # 1. Returns, by which side bounced (see returns.py). The customer's
        #    own bounces count against them; a deposited cheque that the payer
        #    could not honour is reported separately with no penalty.
        side = t.get("bounce_side")
        if side and deb > 0:
            b_type = {
                "OWN": "OUTWARD (OWN PAYMENT / MANDATE RETURNED)",
                "DEPOSIT": "INWARD (DEPOSITED CHEQUE DISHONOURED)",
            }.get(side, "UNRESOLVED (REVIEW)")
            # the payment that bounced and the bank's charge for it are two
            # different amounts: a ₹150 charge row is the charge, and the
            # payment behind it is UNKNOWN unless the statement shows it
            if t.get("return_is_charge"):
                b_amount, b_charge = _bounced_payment(annotated, t), round(deb, 2)
            else:
                b_amount, b_charge = round(deb, 2), None
            bounces.append({
                "date": d_str,
                "type": b_type,
                "bounce_amount": b_amount,
                "bounce_charge": b_charge,
                "is_charge_only": bool(t.get("return_is_charge")),
                "linked_loan": t.get("_linked_loan") or ("N/A" if side == "DEPOSIT" else "UNKNOWN"),
                "loan_link_basis": t.get("_loan_link_basis") or (
                    "deposited cheque: the payer bounced, not a loan" if side == "DEPOSIT" else "-"),
                "narration": narr[:75],
            })

        # 2. Bank Penalties: penal charges and own-return charges only; routine
        #    service charges (SMS, CIBIL, ATM interchange) are not penalties
        if (cat == "BANK_CHARGES" and t.get("subcategory") == "Penal Charge") or \
                (cat == "BOUNCE_PENALTY" and side == "OWN"):
            penalties.append({
                "date": d_str,
                "amount": round(deb, 2),
                "fee_type": _fee_type(narr),
                "narration": narr[:75],
            })

        # 3. Large Outliers
        amt = crd + deb
        if amt >= large_threshold and cat not in ("LOAN_DISBURSEMENT", "SELF_TRANSFER_CR", "SELF_TRANSFER_DR"):
            large_txns.append({
                "date": d_str,
                "direction": "CREDIT" if crd > 0 else "DEBIT",
                "amount": round(amt, 2),
                "balance_after": round(bal, 2) if bal is not None else None,
                "narration": narr[:75],
            })

    # 4. Rapid In-Out Detection (EXCLUDING Self / Internal Transfers) with 5-Factor Confidence Model
    rapid_in_out = []
    dated_txns = [t for t in annotated if t.get("txn_date")]
    related = {(t.get("counterparty") or "").upper() for t in annotated
               if t.get("category", "").startswith("RELATED_PARTY")}
    cr_amts = [float(t["credit"]) for t in dated_txns if t.get("credit") and float(t["credit"]) >= 25000 and not t.get("is_contra")]

    for i, cr_t in enumerate(dated_txns):
        # Ignore self-transfers and reversed pairs
        if cr_t.get("is_contra") or cr_t.get("reversal_pair"):
            continue
        c_amt = float(cr_t["credit"]) if cr_t.get("credit") else 0.0
        if c_amt < 25000:
            continue
        c_date = cr_t["txn_date"]
        c_cp = (cr_t.get("counterparty") or "").strip().upper()
        c_narr = (cr_t.get("narration") or "").upper()

        # Pass-through: the same (or a related) party, the same amount (±1%),
        # in and out within 7 days. Cash is never paired with an unrelated
        # vendor payment: that is how every cash-collection business looks.
        if not c_cp or c_cp in ("UNKNOWN", "CASH", "BANK"):
            continue
        for j in range(i + 1, len(dated_txns)):
            db_t = dated_txns[j]
            d_date = db_t["txn_date"]
            gap_days = (d_date - c_date).days
            if gap_days > 7:
                break
            if db_t.get("is_contra") or db_t.get("reversal_pair"):
                continue
            d_amt = float(db_t["debit"]) if db_t.get("debit") else 0.0
            if d_amt < 25000:
                continue
            d_cp = (db_t.get("counterparty") or "").strip().upper()
            if not (d_cp and (same_party(c_cp, d_cp) or d_cp in related)):
                continue

            diff_ratio = abs(c_amt - d_amt) / c_amt
            if diff_ratio <= 0.01:
                # 1. Time gap (20%)
                time_pts = 20.0 if gap_days == 0 else (15.0 if gap_days == 1 else 10.0)

                # 2. Amount similarity (20%)
                if diff_ratio <= 0.005:
                    sim_pts = 20.0
                elif diff_ratio <= 0.02:
                    sim_pts = 16.0
                elif diff_ratio <= 0.05:
                    sim_pts = 12.0
                else:
                    sim_pts = 6.0

                # 3. Same / Related Counterparty (20%)
                d_cp = (db_t.get("counterparty") or "").strip().upper()
                if c_cp and d_cp and c_cp == d_cp and c_cp not in ("UNKNOWN", "TRANSFER", "NEFT", "RTGS", "UPI"):
                    cp_pts = 20.0
                elif c_cp and d_cp and (c_cp in d_cp or d_cp in c_cp) and len(c_cp) >= 4 and len(d_cp) >= 4:
                    cp_pts = 16.0
                elif c_cp in ("UNKNOWN", "") or d_cp in ("UNKNOWN", ""):
                    cp_pts = 10.0
                else:
                    cp_pts = 4.0

                # 4. Repeated Pattern (20%)
                similar_hits = sum(1 for a in cr_amts if abs(a - c_amt) / c_amt <= 0.10)
                if similar_hits >= 4:
                    rep_pts = 20.0
                elif similar_hits >= 2:
                    rep_pts = 14.0
                else:
                    rep_pts = 6.0

                # 5. Business-Context Mismatch (20%)
                d_narr = (db_t.get("narration") or "").upper()
                has_legit_trade_ref = any(k in c_narr or k in d_narr for k in ("INV", "BILL", "SALARY", "GST", "TAX", "ELECTRICITY", "FEES", "PURCHASE", "ORDER"))
                is_round = (c_amt % 10000 == 0) or (d_amt % 10000 == 0)
                if has_legit_trade_ref:
                    biz_pts = 0.0
                elif is_round:
                    biz_pts = 20.0
                else:
                    biz_pts = 12.0

                total_conf = time_pts + sim_pts + cp_pts + rep_pts + biz_pts
                if total_conf >= 81:
                    conf_level = "VERY HIGH"
                elif total_conf >= 61:
                    conf_level = "HIGH"
                elif total_conf >= 31:
                    conf_level = "MEDIUM"
                else:
                    conf_level = "LOW"

                either_related = any((x.get("category") or "").startswith("RELATED_PARTY") for x in (cr_t, db_t))
                rapid_in_out.append({
                    "counterparty": cr_t.get("counterparty") or "-",
                    "pass_through_type": "RELATED-PARTY" if either_related else "EXTERNAL",
                    "debit_counterparty": db_t.get("counterparty") or "-",
                    "credit_date": c_date.strftime("%d-%b-%Y"),
                    "debit_date": d_date.strftime("%d-%b-%Y"),
                    "credit_amount": round(c_amt, 2),
                    "debit_amount": round(d_amt, 2),
                    "gap_days": gap_days,
                    "confidence_score": round(total_conf, 1),
                    "confidence_level": conf_level,
                    "credit_narration": (cr_t.get("narration") or "")[:45],
                    "debit_narration": (db_t.get("narration") or "")[:45],
                })
                break

    # 5. Window Dressing / EOM Balance Manipulation
    window_dressing_hits = []
    for i, cr_t in enumerate(dated_txns):
        c_date = cr_t["txn_date"]
        c_amt = float(cr_t["credit"]) if cr_t.get("credit") else 0.0
        if c_date.day >= 28 and c_amt >= 50000:
            for j in range(i + 1, min(i + 15, len(dated_txns))):
                db_t = dated_txns[j]
                d_date = db_t["txn_date"]
                d_amt = float(db_t["debit"]) if db_t.get("debit") else 0.0
                if d_date.month != c_date.month and d_date.day <= 4 and abs(c_amt - d_amt) / c_amt <= 0.15:
                    window_dressing_hits.append({
                        "deposit_date": c_date.strftime("%d-%b-%Y"),
                        "withdrawal_date": d_date.strftime("%d-%b-%Y"),
                        "amount": round(c_amt, 2),
                        "deposit_narration": (cr_t.get("narration") or "")[:40],
                        "withdrawal_narration": (db_t.get("narration") or "")[:40],
                    })
                    break

    outward_bounces_cnt = sum(1 for b in bounces if b["type"].startswith("OUTWARD"))
    inward_bounces_cnt = sum(1 for b in bounces if b["type"].startswith("INWARD"))
    total_penalty_amt = sum(p["amount"] for p in penalties)

    # 6. Normalized Cash Flow Deficit Severity
    net_flow = total_inflow - total_outflow
    deficit_severity = "NONE"
    if net_flow < 0:
        deficit_ratio = abs(net_flow) / total_inflow if total_inflow > 0 else 1.0
        if deficit_ratio >= 0.35:
            deficit_severity = "SEVERE (>35% of inflows)"
        elif deficit_ratio >= 0.15:
            deficit_severity = "MODERATE (15-35% of inflows)"
        else:
            deficit_severity = "MILD (<15% of inflows)"

    # Risk summary
    risk_reasons = []
    if outward_bounces_cnt >= 2:
        risk_score = "HIGH"
        risk_reasons.append(f"{outward_bounces_cnt} Outward/ECS Bounces (Acute Default Stress)")
    elif outward_bounces_cnt == 1:
        risk_score = "MODERATE"
        risk_reasons.append("1 Outward Payment/ECS Bounce Detected")
    else:
        risk_score = "LOW"

    if inward_bounces_cnt >= 3:
        if risk_score != "HIGH":
            risk_score = "MODERATE"
        risk_reasons.append(f"{inward_bounces_cnt} Inward Cheque Returns (Customer Credit Stress)")

    if deficit_severity.startswith("SEVERE"):
        risk_reasons.append(f"Severe Cash Deficit: Net Outflows exceed Inflows by {abs(net_flow):,.2f}")

    if len(rapid_in_out) >= 4:
        n_rel = sum(1 for r in rapid_in_out if r["pass_through_type"] == "RELATED-PARTY")
        risk_reasons.append(f"{len(rapid_in_out)} Rapid In-Out / Pass-Through Cycles "
                            f"({len(rapid_in_out) - n_rel} external, {n_rel} related-party)")

    if window_dressing_hits:
        risk_reasons.append(f"{len(window_dressing_hits)} Month-End Window Dressing Cycles Detected")

    is_od = health_data.get("is_overdraft_facility", False)
    avg_util = health_data.get("average_limit_utilization_pct")
    if is_od:
        if avg_util is not None and avg_util > 90.0:
            risk_reasons.append(f"High Overdraft Limit Utilization ({avg_util:.1f}%)")
        turnover_to_limit = health_data.get("credit_turnover_to_limit")
        if turnover_to_limit and turnover_to_limit < 3.0:
            risk_reasons.append(f"Low Credit Turnover to OD Limit ({turnover_to_limit:.1f}x vs 4-6x norm)")

    return {
        # what this module measures: bounces, returns, cash stress. The overall
        # rating is set from the final score in the profiler, so the two never disagree.
        "payment_behaviour_risk": risk_score,
        "overall_risk_rating": risk_score,
        "risk_reasons": risk_reasons,
        "deficit_severity": deficit_severity,
        "net_cash_deficit_amount": round(abs(net_flow), 2) if net_flow < 0 else 0.0,
        "total_bounces_count": len(bounces),
        "inward_bounces_count": inward_bounces_cnt,
        "outward_bounces_count": outward_bounces_cnt,
        "bounces": bounces,
        "total_penalties_count": len(penalties),
        "total_penalty_amount": round(total_penalty_amt, 2),
        "penalties": penalties,
        "peak_negative_overdraft": round(min(neg_balances), 2) if neg_balances else 0.0,
        "large_transactions_count": len(large_txns),
        "large_transactions": large_txns[:15],
        "rapid_in_out_cycles_count": len(rapid_in_out),
        "rapid_in_out_cycles": rapid_in_out[:10],
        "window_dressing_count": len(window_dressing_hits),
        "window_dressing_events": window_dressing_hits,
    }
