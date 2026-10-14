"""Modules 9 & 10: Fraud, Anomaly & AML Monitoring.

Detects duplicate transactions, round amount patterns, circular flows,
and evaluates Potential Structuring / Threshold-Avoidance Patterns with multi-factor confidence scoring.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from typing import Any

from .classifier import classify_all_transactions


_CASH_NARR_RX = re.compile(r"\b(?:BY\s+CASH|CASH\s*DEP\w*|CWDR|ATM|CDM|CASH\s*WDL|CASH)\b", re.I)
_BANK_POSTED_CATS = {"INTEREST_INCOME", "INTEREST_EXPENSE", "BANK_CHARGES", "REFUND_REVERSAL",
                     "BOUNCE_PENALTY", "DEPOSIT_RETURN", "RETURNED_DEPOSIT", "TAX_GST"}
_REVERSAL_RX = re.compile(r"\bREV(?:ERSAL|D)?\b|WRNG|WRONG", re.I)


def _is_cash_row(t: dict) -> bool:
    return t.get("category") in ("CASH_DEPOSIT", "CASH_WITHDRAWAL") or bool(
        _CASH_NARR_RX.search(t.get("narration") or ""))


def _is_bank_posted(t: dict) -> bool:
    return (t.get("category") in _BANK_POSTED_CATS or t.get("counterparty") == "Bank"
            or bool(_REVERSAL_RX.search(t.get("narration") or "")))


def analyze_fraud_and_aml(txns: list[dict], customer_name: str = "") -> dict[str, Any]:
    if not txns or "category" not in txns[0]:
        annotated = classify_all_transactions(txns, customer_name)
    else:
        annotated = txns

    # ----------------------------------------------------------------------
    # 1. Duplicate Transactions
    # ----------------------------------------------------------------------
    # A duplicate posting is the same entry twice in a row: same day, amount,
    # direction, full narration and reference. Same-amount salaries to
    # different staff or two ATM withdrawals carry different references or
    # times and are separate transactions.
    duplicates = []

    def key(t):
        c = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        return (t.get("txn_date"), round(c or deb, 2), "CR" if c > 0 else "DR",
                (t.get("narration") or "").strip().upper(), (t.get("reference") or "").strip().upper())

    for prev, t in zip(annotated, annotated[1:]):
        k = key(t)
        if k[1] >= 500 and k == key(prev):
            for item in (prev, t):
                duplicates.append({
                    "date": item["txn_date"].strftime("%d-%b-%Y") if item.get("txn_date") else "-",
                    "type": k[2],
                    "amount": k[1],
                    "narration": (item.get("narration") or "")[:60],
                    "page": item.get("page", 1),
                })

    # ----------------------------------------------------------------------
    # 2. Round Amount Analysis
    # ----------------------------------------------------------------------
    total_volume = 0.0
    round_volume = 0.0
    round_txns_count = 0
    round_samples = []

    for t in annotated:
        c = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        amt = c + deb
        total_volume += amt

        if amt >= 20000 and amt % 10000 == 0:
            round_volume += amt
            round_txns_count += 1
            if len(round_samples) < 8:
                round_samples.append({
                    "date": t["txn_date"].strftime("%d-%b-%Y") if t.get("txn_date") else "-",
                    "type": "CREDIT" if c > 0 else "DEBIT",
                    "amount": round(amt, 2),
                    "narration": (t.get("narration") or "")[:50],
                })

    round_pct = (round_volume / total_volume * 100) if total_volume > 0 else 0.0

    # ----------------------------------------------------------------------
    # 3. Potential Structuring / Threshold-Avoidance Patterns (Multi-Factor)
    # ----------------------------------------------------------------------
    # Stat thresholds in India: ₹50,000 (PAN requirement), ₹1,00,000, ₹5,00,000 (CTR reporting), ₹10,00,000
    # Threshold avoidance is a cash behaviour. Bank-posted rows (interest,
    # charges, reversals) and ordinary NEFT/RTGS vendor payments that happen
    # to be ₹49,xxx are not candidates.
    candidate_txns = []
    dated_txns = [t for t in annotated if t.get("txn_date") and not t.get("is_contra")]

    for i, t in enumerate(dated_txns):
        c = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        amt = c if c > 0 else deb
        d = t["txn_date"]
        if not _is_cash_row(t) or _is_bank_posted(t):
            continue

        matched_thresh = None
        # Target transactions clustered just below statutory thresholds (within 5-6%)
        if 47000 <= amt < 50000:
            matched_thresh = 50000.0
        elif 95000 <= amt < 100000:
            matched_thresh = 100000.0
        elif 475000 <= amt < 500000:
            matched_thresh = 500000.0
        elif 950000 <= amt < 1000000:
            matched_thresh = 1000000.0

        if matched_thresh is not None:
            dist_pct = (matched_thresh - amt) / matched_thresh * 100.0
            candidate_txns.append({
                "index": i,
                "txn": t,
                "date": d,
                "amount": amt,
                "direction": "CREDIT" if c > 0 else "DEBIT",
                "threshold": matched_thresh,
                "distance_pct": dist_pct,
                "counterparty": (t.get("counterparty") or "").strip().upper(),
                "narration": (t.get("narration") or "").upper(),
            })

    # Precompute counterparty occurrences among candidates
    cp_cand_counts = defaultdict(int)
    for cand in candidate_txns:
        if cand["counterparty"] and cand["counterparty"] not in ("UNKNOWN", "TRANSFER", "NEFT", "RTGS", "UPI"):
            cp_cand_counts[cand["counterparty"]] += 1

    structuring_hits = []
    for cand in candidate_txns:
        c_date = cand["date"]
        c_amt = cand["amount"]
        i = cand["index"]
        c_narr = cand["narration"]

        # 1. 30-day clustering frequency
        freq_30d = sum(
            1 for other in candidate_txns
            if abs((other["date"] - c_date).days) <= 30
        )
        freq_pts = 25.0 if freq_30d >= 3 else (15.0 if freq_30d == 2 else 0.0)

        # 2. Cash nature (every candidate is cash now; kept for the weighting)
        cash_pts = 30.0

        # 3. Proximity to threshold
        if cand["distance_pct"] <= 1.0:
            prox_pts = 30.0
        elif cand["distance_pct"] <= 2.5:
            prox_pts = 20.0
        elif cand["distance_pct"] <= 4.0:
            prox_pts = 10.0
        else:
            prox_pts = 5.0

        # 4. Same counterparty repeat
        cp = cand["counterparty"]
        cp_pts = 15.0 if (cp and cp_cand_counts.get(cp, 0) >= 2) else 0.0

        # 5. Check rapid subsequent debit (within 48 hrs)
        has_rapid_debit = False
        if cand["direction"] == "CREDIT":
            for j in range(i + 1, min(i + 20, len(dated_txns))):
                other = dated_txns[j]
                if (other["txn_date"] - c_date).days > 2:
                    break
                d_amt = float(other["debit"]) if other.get("debit") else 0.0
                if d_amt >= 20000 and abs(c_amt - d_amt) / c_amt <= 0.20:
                    has_rapid_debit = True
                    break
        rapid_pts = 15.0 if has_rapid_debit else 0.0

        # 6. Legitimate business purpose discount
        has_legit_trade = any(k in c_narr for k in ("INV", "BILL", "SALARY", "GST", "TAX", "ELECTRICITY", "FEES", "PURCHASE", "ORDER", "SUPPLIER"))
        trade_discount = 20.0 if has_legit_trade else 0.0

        score = cash_pts + prox_pts + freq_pts + cp_pts + rapid_pts - trade_discount

        # Filter out normal business sizes that lack suspicious patterns
        if score >= 55.0:
            confidence = "HIGH"
        elif score >= 30.0:
            confidence = "MEDIUM"
        elif cand["distance_pct"] <= 2.5 and not has_legit_trade:
            confidence = "LOW"
        else:
            continue  # Normal commercial transaction size, not structuring

        structuring_hits.append({
            "date": c_date.strftime("%d-%b-%Y"),
            "direction": cand["direction"],
            "amount": round(c_amt, 2),
            "threshold_avoided": f"₹{cand['threshold']:,.0f}",
            "distance_pct": round(cand["distance_pct"], 2),
            "frequency_30d": freq_30d,
            "rapid_debit_observed": has_rapid_debit,
            "confidence_level": confidence,
            "narration": (cand["txn"].get("narration") or "")[:60],
        })

    # ----------------------------------------------------------------------
    # 4. High-Value Transactions (>= ₹10 Lakhs)
    # ----------------------------------------------------------------------
    high_value_txns = []
    for t in annotated:
        c = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        amt = c if c > 0 else deb
        if amt >= 1000000.0:
            high_value_txns.append({
                "date": t["txn_date"].strftime("%d-%b-%Y") if t.get("txn_date") else "-",
                "direction": "CREDIT" if c > 0 else "DEBIT",
                "amount": round(amt, 2),
                "narration": (t.get("narration") or "")[:65],
            })

    # ----------------------------------------------------------------------
    # 5. Circular / Reciprocal Flow Detection (Excluding Self Transfers)
    # ----------------------------------------------------------------------
    in_by_party = defaultdict(float)
    out_by_party = defaultdict(float)
    for t in annotated:
        if t.get("is_contra"):
            continue
        cp = t.get("counterparty") or "Unknown"
        if cp in {"Unknown", "Cash", "Atm", "Self", "Transfer"}:
            continue
        c = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        in_by_party[cp] += c
        out_by_party[cp] += deb

    circular_flows = []
    for cp in set(in_by_party.keys()) & set(out_by_party.keys()):
        in_val = in_by_party[cp]
        out_val = out_by_party[cp]
        if in_val >= 25000 and out_val >= 25000:
            diff = abs(in_val - out_val)
            min_val = min(in_val, out_val)
            if diff / min_val <= 0.35:
                circular_flows.append({
                    "counterparty": cp,
                    "inward_amount": round(in_val, 2),
                    "outward_amount": round(out_val, 2),
                    "net_difference": round(diff, 2),
                })

    total_cr = sum(float(t["credit"]) for t in annotated if t.get("credit"))
    cash_cr = sum(float(t["credit"]) for t in annotated if t.get("credit") and t.get("category") == "CASH_DEPOSIT")
    cash_share = (cash_cr / total_cr * 100) if total_cr else 0.0
    business_model_flags = []
    if cash_share >= 50.0:
        business_model_flags.append(
            f"Cash-heavy account: {cash_share:.1f}% of inflows are cash deposits; in-out pairing "
            f"and structuring counts should be read in that light")

    return {
        "cash_deposit_share_pct": round(cash_share, 2),
        "business_model_flags": business_model_flags,
        "duplicates_count": len(duplicates),
        "duplicates": duplicates[:10],
        "round_amount_transactions_count": round_txns_count,
        "round_amount_share_pct": round(round_pct, 2),
        "round_amount_samples": round_samples,
        "structuring_alerts_count": len(structuring_hits),
        "structuring_alerts": structuring_hits[:15],
        "high_value_transactions_count": len(high_value_txns),
        "high_value_transactions": high_value_txns[:10],
        "circular_flows_detected_count": len(circular_flows),
        "circular_flows": circular_flows[:6],
    }
