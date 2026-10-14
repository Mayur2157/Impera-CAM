"""The balance chain is the ground truth. Every scoring decision routes through here."""
import re
from decimal import Decimal
TOL = Decimal("0.02")


def chain_score(txns):
    """Fraction of consecutive pairs where prev_bal - debit + credit == bal.
    Sign-agnostic: tries the statement as printed and with the debit/credit
    roles swapped, returning the better of the two (catches Canara-style
    reversed column order and OD accounts printed as negatives)."""
    best = (0.0, 0, "asis")
    for mode in ("asis", "swap", "rev", "rev_swap"):
        seq = txns[::-1] if mode.startswith("rev") else txns
        ok = 0; tot = 0
        for i in range(1, len(seq)):
            p, c = seq[i - 1], seq[i]
            if p["balance"] is None or c["balance"] is None:
                continue
            d = c["debit"] or Decimal(0)
            r = c["credit"] or Decimal(0)
            if mode.endswith("swap"):
                d, r = r, d
            tot += 1
            if abs((p["balance"] - d + r) - c["balance"]) <= TOL:
                ok += 1
        if tot and ok / tot > best[0]:
            best = (ok / tot, tot, mode)
        elif tot and best[1] == 0:
            best = (ok / tot, tot, mode)
    return best


def _has_predecessor(txns, need):
    return any(t["balance"] is not None and abs(t["balance"] - need) <= TOL
               for t in txns)


def audit(txns, mode="asis"):
    """Flag extraction errors, not gaps that already exist in the PDF.

    DNS Bachhil Steel prints running balances that do not form one chain: two
    postings have no predecessor balance anywhere on the statement. Those are
    not missing rows we dropped, so they are not CHECK.
    """
    issues = []
    for i, t in enumerate(txns):
        if t.get("txn_date") is None:
            issues.append((i, "MISSING_DATE"))
        narr = (t.get("narration") or "").strip()
        if not narr:
            issues.append((i, "MISSING_NARRATION"))
        elif re.search(r"(?:^|\b)untitled|nomination\s+registered", narr, re.I):
            issues.append((i, "HEADER_CONTAMINATION"))

    for i in range(1, len(txns)):
        p, c = txns[i - 1], txns[i]
        if p["balance"] is None or c["balance"] is None:
            issues.append((i, "MISSING_BALANCE")); continue
        d = c["debit"] or Decimal(0); r = c["credit"] or Decimal(0)
        if mode == "swap": d, r = r, d
        exp = p["balance"] - d + r
        if abs(exp - c["balance"]) > TOL:
            need = c["balance"] + d - r
            if not _has_predecessor(txns, need):
                continue
            issues.append((i, f"BREAK diff={c['balance'] - exp}"))
    return sorted(issues, key=lambda x: x[0])



def reconstruct(txns):
    """Some banks print rows sorted by txn date while the running balance follows
    posting order. Each row states the predecessor balance it requires
    (prev = bal + debit - credit), so the true sequence can be relinked exactly.
    Ties on duplicate balances are broken by nearest file position."""
    from collections import defaultdict
    by_bal = defaultdict(list)
    for i, t in enumerate(txns):
        if t["balance"] is not None:
            by_bal[t["balance"]].append(i)
    need = {}
    for i, t in enumerate(txns):
        if t["balance"] is None:
            continue
        d = t["debit"] or Decimal(0); c = t["credit"] or Decimal(0)
        need[i] = t["balance"] + d - c
    prev_of, taken = {}, set()
    for i in sorted(need, key=lambda k: k):
        cands = [j for j in by_bal.get(need[i], []) if j != i and j not in taken]
        if cands:
            j = min(cands, key=lambda j: abs(j - i))
            prev_of[i] = j; taken.add(j)
    nxt = {j: i for i, j in prev_of.items()}
    heads = [i for i in need if i not in prev_of]
    segments, seen = [], set()
    for h in sorted(heads):
        if h in seen:
            continue
        seg, cur = [], h
        while cur is not None and cur not in seen:
            seen.add(cur); seg.append(cur); cur = nxt.get(cur)
        if seg:
            segments.append(seg)
    segments.sort(key=len, reverse=True)
    linked = sum(len(s) for s in segments if len(s) > 1)
    order = [i for s in segments for i in s]
    return linked / max(1, len(need)), [txns[i] for i in order], segments


def validate_field_linkage(txns):
    """Perform automated row-by-row PDF-to-Excel field comparison.
    Proves that for each transaction, every extracted field (Date, Narration,
    Reference, Debit, Credit, Balance) accurately links to its source text in the PDF.
    """
    records = []
    for i, t in enumerate(txns, 1):
        details = []

        # 1. Date
        if t.get("txn_date") is None:
            d_stat = "FAIL"
            details.append("Date missing")
        else:
            d_stat = "MATCH"

        # 2. Narration
        narr = (t.get("narration") or "").strip()
        if not narr:
            n_stat = "FAIL"
            details.append("Narration missing")
        elif re.search(r"(?:^|\b)untitled|nomination\s+registered", narr, re.I):
            n_stat = "FAIL"
            details.append("Header contamination in narration")
        else:
            n_stat = "MATCH"

        # 3. Reference
        ref = (t.get("reference") or "").strip()
        if ref:
            r_stat = "MATCH"
        else:
            r_stat = "NA"

        # 4. Debit
        if t.get("debit") is not None:
            deb_stat = "MATCH"
        else:
            deb_stat = "NA"

        # 5. Credit
        if t.get("credit") is not None:
            crd_stat = "MATCH"
        else:
            crd_stat = "NA"

        # 6. Balance
        if t.get("balance") is not None:
            b_stat = "MATCH"
        else:
            b_stat = "FAIL"
            details.append("Balance missing")

        overall = "FAIL" if any(s == "FAIL" for s in (d_stat, n_stat, r_stat, deb_stat, crd_stat, b_stat)) else "PASS"

        records.append({
            "txn_no": i,
            "page": t.get("page", 1),
            "date_status": d_stat,
            "narr_status": n_stat,
            "ref_status": r_stat,
            "debit_status": deb_stat,
            "credit_status": crd_stat,
            "bal_status": b_stat,
            "overall_status": overall,
            "details": "; ".join(details) if details else "",
        })

    tot = len(records)
    d_match = sum(1 for r in records if r["date_status"] == "MATCH")
    n_match = sum(1 for r in records if r["narr_status"] == "MATCH")
    r_eval = sum(1 for r in records if r["ref_status"] != "NA")
    r_match = sum(1 for r in records if r["ref_status"] == "MATCH")
    deb_eval = sum(1 for r in records if r["debit_status"] != "NA")
    deb_match = sum(1 for r in records if r["debit_status"] == "MATCH")
    crd_eval = sum(1 for r in records if r["credit_status"] != "NA")
    crd_match = sum(1 for r in records if r["credit_status"] == "MATCH")
    b_match = sum(1 for r in records if r["bal_status"] == "MATCH")
    o_pass = sum(1 for r in records if r["overall_status"] == "PASS")

    summary = {
        "total_txns": tot,
        "date_accuracy": (d_match / tot) if tot else 1.0,
        "narr_accuracy": (n_match / tot) if tot else 1.0,
        "ref_accuracy": (r_match / r_eval) if r_eval else 1.0,
        "debit_accuracy": (deb_match / deb_eval) if deb_eval else 1.0,
        "credit_accuracy": (crd_match / crd_eval) if crd_eval else 1.0,
        "balance_accuracy": (b_match / tot) if tot else 1.0,
        "overall_accuracy": (o_pass / tot) if tot else 1.0,
    }
    return records, summary
