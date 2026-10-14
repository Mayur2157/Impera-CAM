"""Module 6: Transaction Behaviour & Channels.

Classifies transactions by channel (UPI, NEFT, RTGS, IMPS, Cash, Cheque, POS, etc.),
analyzes volume share, velocity, and daily/weekday transaction patterns.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .narration_rules import detect_channel


def analyze_channels(txns: list[dict]) -> dict[str, Any]:
    channel_stats = defaultdict(lambda: {
        "credit_count": 0, "debit_count": 0, "total_count": 0,
        "credit_amount": 0.0, "debit_amount": 0.0, "total_amount": 0.0,
    })

    weekday_counts = defaultdict(int)
    day_counts = defaultdict(int)

    total_amount_all = 0.0

    for t in txns:
        narr = t.get("narration") or ""
        ch = detect_channel(narr)
        crd = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        amt = crd + deb
        total_amount_all += amt

        stats = channel_stats[ch]
        stats["total_count"] += 1
        stats["total_amount"] += amt
        if crd > 0:
            stats["credit_count"] += 1
            stats["credit_amount"] += crd
        if deb > 0:
            stats["debit_count"] += 1
            stats["debit_amount"] += deb

        d = t.get("txn_date")
        if d:
            day_counts[d] += 1
            w_name = d.strftime("%A")
            weekday_counts[w_name] += 1

    channel_breakdown = []
    for ch, s in channel_stats.items():
        pct = (s["total_amount"] / total_amount_all * 100) if total_amount_all > 0 else 0.0
        channel_breakdown.append({
            "channel": ch,
            "total_count": s["total_count"],
            "credit_count": s["credit_count"],
            "debit_count": s["debit_count"],
            "credit_amount": round(s["credit_amount"], 2),
            "debit_amount": round(s["debit_amount"], 2),
            "total_amount": round(s["total_amount"], 2),
            "volume_share_pct": round(pct, 2),
        })

    channel_breakdown.sort(key=lambda x: x["total_amount"], reverse=True)

    # Velocity & Day patterns
    num_active_days = len(day_counts) or 1
    total_txns = len(txns)
    avg_txns_per_day = total_txns / num_active_days

    weekday_total = sum(v for k, v in weekday_counts.items() if k not in ("Saturday", "Sunday"))
    weekend_total = sum(v for k, v in weekday_counts.items() if k in ("Saturday", "Sunday"))
    weekday_pct = (weekday_total / total_txns * 100) if total_txns > 0 else 0.0
    weekend_pct = (weekend_total / total_txns * 100) if total_txns > 0 else 0.0

    return {
        "channels": channel_breakdown,
        "total_transactions": total_txns,
        "active_days_count": num_active_days,
        "avg_transactions_per_day": round(avg_txns_per_day, 2),
        "weekday_share_pct": round(weekday_pct, 2),
        "weekend_share_pct": round(weekend_pct, 2),
        "weekday_distribution": dict(weekday_counts),
    }
