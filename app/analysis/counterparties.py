"""Module 7: Counterparty Analysis.

Identifies counterparties, top customers/inflows, top vendors/outflows,
lenders, self-transfers, and evaluates concentration exposure.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import re

from .classifier import classify_all_transactions
from .narration_rules import norm_name, same_name_variant as _same_name_variant

_NOT_PARTIES = {"Unknown", "Cash", "Bank", "Tax Authority"}
_ACCOUNT_LABEL_RX = re.compile(r"\b(?:ACCOUNTS?|A/C|POOL(?:ING)?|NODAL|SETTLEMENT|ESCROW|SUSPENSE|CLEARING)\b", re.I)


def _merge_near_duplicates(parties: dict) -> dict:
    """'PAPER FLUTINGS' and 'PAPER FLUTTINGS' are one payee (see _same_name_variant)."""
    names = sorted(parties, key=lambda k: -parties[k]["amount"])
    canon: dict[str, str] = {}
    for n in names:
        for c in set(canon.values()):
            if _same_name_variant(n, c):
                canon[n] = c
                break
        else:
            canon[n] = n
    merged = defaultdict(lambda: {"count": 0, "amount": 0.0, "dates": []})
    for n, rec in parties.items():
        m = merged[canon[n]]
        m["count"] += rec["count"]
        m["amount"] += rec["amount"]
        m["dates"] += rec["dates"]
    return merged


def analyze_counterparties(txns: list[dict], customer_name: str = "") -> dict[str, Any]:
    if txns and "category" not in txns[0]:
        txns = classify_all_transactions(txns, customer_name)
    inward_parties = defaultdict(lambda: {"count": 0, "amount": 0.0, "dates": []})
    outward_parties = defaultdict(lambda: {"count": 0, "amount": 0.0, "dates": []})
    related_parties = defaultdict(lambda: {"in": 0.0, "out": 0.0, "count": 0, "names": defaultdict(float),
                                           "basis": "-", "purposes": defaultdict(float)})

    total_credits = sum(float(t["credit"]) for t in txns if t.get("credit"))
    total_debits = sum(float(t["debit"]) for t in txns if t.get("debit"))

    self_transfers = []
    lender_parties = defaultdict(lambda: {"count": 0, "amount": 0.0})
    funding = defaultdict(lambda: {"count": 0, "amount": 0.0})
    bank_payers: dict[str, float] = {}

    for t in txns:
        narr = t.get("narration") or ""
        cp = t.get("counterparty") or "Unknown"
        cat = t.get("category") or ""
        crd = float(t["credit"]) if t.get("credit") else 0.0
        deb = float(t["debit"]) if t.get("debit") else 0.0
        d_str = t["txn_date"].strftime("%d-%b-%Y") if t.get("txn_date") else "-"

        # a debit and the reversal that undid it are no flow at all
        if t.get("reversal_pair"):
            continue
        if cat == "BANK_FUNDED_INFLOW":
            # a bank paying in is not a customer: listed for review, not ranked
            bank_payers[cp] = bank_payers.get(cp, 0.0) + crd
            continue
        # The classifier decided own-account vs related vs arm's-length
        is_self = bool(t.get("is_contra"))
        if is_self:
            self_transfers.append({
                "date": d_str,
                "type": "CREDIT" if crd > 0 else "DEBIT",
                "amount": round(crd if crd > 0 else deb, 2),
                "party": cp,
                "narration": narr[:60],
            })
            continue
        # one relationship per counterparty (entities.py): every row of a
        # related party is reported with it, whatever that row was for, and
        # none of them also appears as a customer or vendor
        if t.get("relationship") == "RELATED_PARTY" or cat.startswith("RELATED_PARTY"):
            rp = related_parties[t.get("counterparty_id") or cp]
            rp["in"] += crd
            rp["out"] += deb
            rp["count"] += 1
            rp["names"][cp] += crd + deb
            rp["basis"] = t.get("relationship_basis") or "-"
            purpose = t.get("purpose") or t.get("subcategory") or cat
            rp["purposes"][purpose] += crd + deb
            continue

        # borrowed money is a funding source, not a customer
        if crd > 0 and (cat == "LOAN_DISBURSEMENT" or t.get("is_financing")):
            funding[cp]["amount"] += crd
            funding[cp]["count"] += 1
            continue

        if crd > 0:
            rec = inward_parties[cp]
            rec["count"] += 1
            rec["amount"] += crd
            rec["dates"].append(d_str)

        if deb > 0:
            rec = outward_parties[cp]
            rec["count"] += 1
            rec["amount"] += deb
            rec["dates"].append(d_str)
            if cat == "LOAN_EMI":
                l_rec = lender_parties[cp]
                l_rec["count"] += 1
                l_rec["amount"] += deb

    inward_parties = _merge_near_duplicates(inward_parties)
    outward_parties = _merge_near_duplicates(outward_parties)

    # Format Top Inward
    top_inward = []
    for cp, data in inward_parties.items():
        if cp in _NOT_PARTIES:
            continue
        share = (data["amount"] / total_credits * 100) if total_credits > 0 else 0.0
        top_inward.append({
            "counterparty": cp,
            "count": data["count"],
            "total_amount": round(data["amount"], 2),
            "share_pct": round(share, 2),
            "last_date": data["dates"][-1] if data["dates"] else "-",
        })
    top_inward.sort(key=lambda x: x["total_amount"], reverse=True)

    # Format Top Outward
    top_outward = []
    for cp, data in outward_parties.items():
        if cp in _NOT_PARTIES:
            continue
        share = (data["amount"] / total_debits * 100) if total_debits > 0 else 0.0
        top_outward.append({
            "counterparty": cp,
            "count": data["count"],
            "total_amount": round(data["amount"], 2),
            "share_pct": round(share, 2),
            "last_date": data["dates"][-1] if data["dates"] else "-",
        })
    top_outward.sort(key=lambda x: x["total_amount"], reverse=True)

    # Concentration metrics
    top1_inward_pct = top_inward[0]["share_pct"] if top_inward else 0.0
    top3_inward_pct = sum(x["share_pct"] for x in top_inward[:3])
    top1_outward_pct = top_outward[0]["share_pct"] if top_outward else 0.0
    top3_outward_pct = sum(x["share_pct"] for x in top_outward[:3])

    top_lenders = [
        {"lender": k, "count": v["count"], "total_amount": round(v["amount"], 2)}
        for k, v in sorted(lender_parties.items(), key=lambda x: x[1]["amount"], reverse=True)
    ]

    total_self_transfer_val = sum(x["amount"] for x in self_transfers)

    return {
        "top_inward_parties": top_inward[:10],
        "top_outward_parties": top_outward[:10],
        "top_lenders": top_lenders[:6],
        "self_transfers": self_transfers,
        "funding_sources": [
            {"source": k, "count": v["count"], "total_amount": round(v["amount"], 2)}
            for k, v in sorted(funding.items(), key=lambda x: -x[1]["amount"])
        ],
        # named like an account, not a party ('WORKING ACCOUNTS', 'NODAL A/C'):
        # possibly internal / pooled / group money; kept in the figures but flagged
        "review_counterparties": [
            {"counterparty": x["counterparty"], "total_amount": x["total_amount"],
             "reason": "Named like an account rather than a party — possible internal / pooled / group funding"}
            for x in top_inward if _ACCOUNT_LABEL_RX.search(x["counterparty"])
        ] + [
            {"counterparty": cp, "total_amount": round(amt, 2),
             "reason": "Paid in by a bank — confirm whether loan, OD or a customer's remittance"}
            for cp, amt in bank_payers.items()
        ],
        "possible_related_parties": [
            {"counterparty": max(v["names"], key=v["names"].get) if v["names"] else k, "counterparty_id": k,
             "name_variants": sorted(v["names"]),
             "inflow": round(v["in"], 2), "outflow": round(v["out"], 2), "count": v["count"],
             "relationship_basis": v["basis"],
             "purposes": [{"purpose": pk, "amount": round(pv, 2)}
                          for pk, pv in sorted(v["purposes"].items(), key=lambda x: -x[1])]}
            for k, v in sorted(related_parties.items(), key=lambda x: -(x[1]["in"] + x[1]["out"]))
        ],
        "self_transfer_count": len(self_transfers),
        "total_self_transfer_amount": round(total_self_transfer_val, 2),
        "concentration": {
            "top1_inward_share_pct": round(top1_inward_pct, 2),
            "top3_inward_share_pct": round(top3_inward_pct, 2),
            "top1_outward_share_pct": round(top1_outward_pct, 2),
            "top3_outward_share_pct": round(top3_outward_pct, 2),
            "customer_concentration_risk": "HIGH" if top3_inward_pct > 60 else ("MODERATE" if top3_inward_pct > 40 else "LOW"),
            "vendor_concentration_risk": "HIGH" if top3_outward_pct > 60 else ("MODERATE" if top3_outward_pct > 40 else "LOW"),
        },
    }
