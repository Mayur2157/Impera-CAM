"""End to end: one PDF in, one workbook out, plus a machine readable summary."""
from __future__ import annotations

import os
import re
from decimal import Decimal

import pdfplumber

from .extract import extract
from .customer import extract_customer
from .annexure import attach_party_hints, parse_party_annexure
from . import registry
from .validate import audit, reconstruct, chain_score
from ..output.excel import write_workbook

MIN_SCORE = 0.98        # below this, try relinking before giving up


def _sum(txns, key):
    return sum((t[key] or Decimal(0)) for t in txns)


def check_completeness(pdf, info: dict, txns: list[dict]) -> tuple[bool, str]:
    """Detect whether the PDF is a truncated/partial excerpt of a longer statement."""
    num_pages = len(pdf.pages)
    page_footer_rx = re.compile(r"\bpage\s+(\d+)\s*(?:of|o|\||/)\s*(\d+)\b", re.I)
    footer_detected = None

    for p in pdf.pages:
        txt = p.extract_text() or ""
        for m in page_footer_rx.finditer(txt):
            cur, tot = int(m.group(1)), int(m.group(2))
            if tot >= cur and tot <= 1000:
                if (footer_detected is None or tot > footer_detected[1] or
                        (tot == footer_detected[1] and cur > footer_detected[0])):
                    footer_detected = (cur, tot)

    pages_complete = False
    if footer_detected:
        cur, tot = footer_detected
        if num_pages < tot:
            return True, f"PARTIAL: PDF contains {num_pages} of {tot} pages (footer prints Page {cur} of {tot})"
        pages_complete = cur == tot and num_pages >= tot

    period_to = info.get("period_to")
    if hasattr(period_to, "year"):
        dates = sorted(t["txn_date"] for t in txns if t.get("txn_date") and hasattr(t["txn_date"], "year"))
        if dates:
            last_date = dates[-1]
            gap_days = (period_to - last_date).days
            # a quiet end of period is not missing pages: it counts as a cut
            # only when the footers do not show every page AND the gap is
            # longer than any gap between this account's own transactions
            longest_inside = max(((b - a).days for a, b in zip(dates, dates[1:])), default=0)
            if gap_days >= 7 and not pages_complete and gap_days > longest_inside:
                return True, (
                    f"PARTIAL: Transactions end on {last_date.strftime('%d-%b-%Y')} "
                    f"but statement period ends on {period_to.strftime('%d-%b-%Y')} "
                    f"({gap_days} days missing from source PDF; longest gap between its "
                    f"transactions is {longest_inside} days)"
                )
            if gap_days >= 7:
                why = "footer shows every page" if pages_complete else \
                      f"no longer than its own longest gap ({longest_inside} days)"
                return False, f"COMPLETE — no transactions in the last {gap_days} days of the period ({why})"

    return False, "COMPLETE"


def process(pdf_path: str, out_dir: str, password: str | None = None,
            use_ocr: bool = True, dpi: int = 300, backend: str | None = None,
            progress=None, source_name: str | None = None, bank: str | None = None,
            tenant_id: str | None = None) -> dict:
    def say(pct, msg):
        if progress:
            progress(pct, msg)

    say(5, "reading pages")
    strat, (score, npairs, mode, txns), _all, htop, report = extract(
        pdf_path, password=password, use_ocr=use_ocr, dpi=dpi, backend=backend)
    if not txns:
        raise RuntimeError("no transaction table found in this PDF")

    scanned = [r.page for r in report if r.scanned]
    say(55, f"{len(txns)} rows parsed, verifying balance chain")

    seq = txns[::-1] if mode.startswith("rev") else txns
    recon = 0.0
    if score < MIN_SCORE:
        say(60, "print order does not match posting order, relinking")
        cov, relinked, _segments = reconstruct(seq)
        if relinked and chain_score(relinked)[0] > score:
            seq, recon = relinked, cov
            score = max(score, chain_score(relinked)[0])

    issues = audit(seq, "swap" if mode.endswith("swap") else "asis")

    say(75, "reading account details")
    clean_source = source_name or re.sub(r"^[0-9a-f]{8}_", "", os.path.basename(pdf_path))
    with pdfplumber.open(pdf_path, password=password) as pdf:
        info = extract_customer(pdf, htop, source_name=clean_source)
        # a bank named by the user fills in when the statement prints its name
        # only as a logo (Cosmos 'Imperative', Kotak); the statement's own text wins
        if bank and info.get("bank_source") != "statement":
            info["bank"], info["bank_source"] = bank.strip(), "supplied"
        is_partial, completeness = check_completeness(pdf, info, seq)
        attach_party_hints(seq, parse_party_annexure(pdf))

    opening = None
    if seq:
        opening = seq[0]["balance"] + (seq[0]["debit"] or Decimal(0)) \
                  - (seq[0]["credit"] or Decimal(0))

    meta = {
        "source": clean_source,
        "strategy": strat, "mode": mode, "score": score, "recon": recon,
        "opening": opening,
        "closing": seq[-1]["balance"] if seq else None,
        "scanned_pages": scanned,
        "pages": len(report),
        "is_partial": is_partial,
        "completeness": completeness,
        # a layout the exact column labels did not read: header words matched instead
        "column_headers": "matched by words (unfamiliar layout — review)"
                          if (_all or {}).get("_word_fallback") else "matched exactly",
    }

    say(82, "generating customer financial profile")
    from app.analysis.profiler import generate_financial_profile
    # accounts of holders seen in earlier statements who share this holder's
    # email / mobile / address; then remember this holder for later ones
    info["linked_accounts"] = registry.linked_accounts(info, tenant_id=tenant_id)
    profile = generate_financial_profile(seq, info, meta, issues)
    registry.register(info, tenant_id=tenant_id)

    say(88, "writing workbook")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    out = os.path.join(out_dir, f"{stem}.xlsx")
    write_workbook(out, seq, info, issues, meta, profile=profile)
    say(100, "done")

    return {
        "xlsx": out,
        "filename": os.path.basename(out),
        "rows": len(seq),
        "chain": float(score),
        "flagged": len(issues),
        "strategy": strat,
        "mode": mode,
        "reconstructed": float(recon),
        "pages": len(report),
        "scanned_pages": scanned,
        "is_partial": is_partial,
        "completeness": completeness,
        "financial_profile": profile["executive_summary"],
        "info": {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                 for k, v in info.items()},
        "totals": {
            "debit": float(_sum(seq, "debit")),
            "credit": float(_sum(seq, "credit")),
            "opening": float(opening) if opening is not None else None,
            "closing": float(seq[-1]["balance"]) if seq else None,
        },
    }

