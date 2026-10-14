"""Narration-boundary and page chrome cleaning.

Amounts and the running-balance chain are already trustworthy. The remaining
errors are (1) page-footer / disclaimer prose glued onto the last transaction
of a page and (2) opening-balance / rule-line stubs emitted as fake rows.

This module is string-level on purpose so it cannot disturb column geometry.
Callers decide which *lines* to drop; we only say whether the text is chrome.
"""
from __future__ import annotations

import re
from collections import Counter

from .normalize import parse_amount, parse_date

# Phrases that never belong in a transaction narration. Built from footers
# that leaked in Union / HDFC / Bandhan / Bharat Co-op statements — keep them
# generic so a new bank's disclaimer is caught without a per-bank dictionary.
FOOTER_HINT = re.compile(
    r"(for any queries|queries,?\s+please|please get in touch|system generated|"
    r"computer generated|this is a\s+(computer|system)\s+generated|"
    r"earmarked for hold|uncleared funds|"
    r"considered correct if no error|error is reported within|"
    r"deposit insurance|dicgc|"
    r"notifies the bank|notifies the constituent|"
    r"unless the constituent|discrepancy in (this |the )?statement|"
    r"disclaimer\s*:|generated on\s*~?finx|proprietary software|"
    r"schedule of charges|each depositor|"
    r"registered office|gstin number|branch gstn|"
    r"to avail our loan products|give missed call|"
    r"please do not share|bank never asks|"
    r"page\s*no\.?\s*\d|page\s+\d+\s+of\s+\d|"
    r"this statement\.?\s*$|"
    r"https?://|www\.[a-z0-9]|customer\s*care)",
    re.I,
)

PAGE_MARKER = re.compile(
    r"^\s*(page\s*(no\.?)?\s*\d+|page\s+\d+(\s+of\s+\d+)?|page\s+\d+\s*\|\s*\d+)\s*$", re.I)

SEPARATOR = re.compile(r"^[\-\u2013\u2014=_~]{8,}$")

OPENING = re.compile(
    r"opening\s*balance|(?:date)?\s*b\s*/\s*f\b|\bc\s*/\s*f\b|"
    r"brought\s*forward|carried\s*forward", re.I)

BANK_LEGAL = re.compile(
    r"\bbank\b.*(limited|ltd\.?|of india)|^(the\s+)?[a-z&. ]+\s+bank(\s+limited|\s+ltd\.?)?$",
    re.I,
)

# A stub narration that is really a column/header leftover.
STUB_NARR = re.compile(r"^(balance|opening|closing|total|particulars?|narration)?$", re.I)

# Disclaimer/address prose is grammatical English; a repeated counterparty name
# (SBI 'Mor transport company / Mor transport', a payee billed many times) is
# not. Require a few function words before a long repeated line is chrome, so
# a frequent payee's name does not get deleted out of its own narration.
_STOPWORDS = {
    "the", "is", "of", "in", "on", "for", "to", "a", "an", "and", "or", "this",
    "that", "your", "our", "any", "please", "will", "are", "has", "have", "not",
    "no", "with", "us", "by", "if", "as", "at", "be", "it", "which", "within",
    "up", "out", "per", "from", "does", "may", "shall", "you", "we",
}


def _looks_like_prose(t: str) -> bool:
    words = re.findall(r"[a-z]+", t)
    return sum(1 for w in words if w in _STOPWORDS) >= 3


def norm_line(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def looks_like_footer(text: str) -> bool:
    t = norm_line(text)
    if not t:
        return False
    if SEPARATOR.match(t) or PAGE_MARKER.match(t):
        return True
    return bool(FOOTER_HINT.search(t))


def looks_like_separator(text: str) -> bool:
    return bool(SEPARATOR.match(norm_line(text)))


def repeated_line_keys(page_texts: list[list[str]], min_len: int = 16) -> set[str]:
    """Exact (and long-prefix) lines that appear on two or more pages.

    Short repeating narrations such as ``BY CASH`` are ignored — those are
    real transactions. Callers should only feed *non-balance* line texts so a
    transaction row cannot vote itself into the footer set.
    """
    per_page = []
    for lines in page_texts:
        keys = set()
        for raw in lines:
            t = norm_line(raw).lower()
            if len(t) < min_len:
                continue
            keys.add(t)
            if len(t) >= 40:
                keys.add(t[:64])
        per_page.append(keys)
    counts: Counter[str] = Counter()
    for keys in per_page:
        counts.update(keys)
    return {k for k, n in counts.items() if n >= 2}


def is_repeated_boilerplate(text: str, repeats: set[str], min_len: int = 24) -> bool:
    t = norm_line(text).lower()
    if len(t) < 12:
        return False
    # Same counterparty VPA / UPI path can print on many pages; that is a
    # real wrap line, not a footer (Canara SO/MAHB/**85866@YBL/RETU).
    if re.search(r"(@|\*\*|upi/|neft|imps|rtgs|chq:)", t, re.I):
        return False
    hit = t in repeats or (len(t) >= 40 and t[:64] in repeats)
    if not hit:
        return False
    # Long repeats are footers only when they read as prose (disclaimers,
    # addresses) -- a long repeated line with no function words is more
    # likely a frequent payee's name than boilerplate. Short repeats are only
    # chrome when they are a bank legal line ('HDFC BANK LIMITED') -- not
    # wrapped narration such as 'Customer Payment' which can legitimately
    # recur.
    if len(t) >= min_len:
        return _looks_like_prose(t)
    return bool(BANK_LEGAL.search(t)) and not re.search(r"[\d/]", t)


def is_chrome_line(text: str, repeats: set[str] | None = None) -> bool:
    t = norm_line(text).lower()
    if t == "untitled":
        return True
    if looks_like_footer(text):
        return True
    if repeats and is_repeated_boilerplate(text, repeats):
        return True
    return False


def scrub_field(text: str | None) -> str:
    """Cut a glued-on footer off the end of a narration/reference cell."""
    t = norm_line(text)
    if not t:
        return ""
    if looks_like_separator(t):
        return ""
    # Strip leading Untitled document artifact
    t = re.sub(r"^untitled\b\s*", "", t, flags=re.I).strip()
    m = FOOTER_HINT.search(t)
    if m:
        if m.start() < 4:
            return ""
        t = t[:m.start()].strip(" ,;:-")
    return t


def is_stub_row(row: dict) -> bool:
    """Opening-balance / rule-line / header leftover — not a posting."""
    date_raw = row.get("txn_date") or ""
    narr = norm_line(row.get("narration"))
    ref = norm_line(row.get("reference"))
    debit_raw = row.get("debit") or ""
    credit_raw = row.get("credit") or ""
    amount_raw = row.get("amount") or ""
    blob = " ".join(x for x in (date_raw, narr, ref, debit_raw, credit_raw, amount_raw) if x)

    if OPENING.search(blob):
        return True
    if looks_like_separator(ref) or looks_like_separator(narr):
        return True
    if looks_like_footer(narr) and parse_amount(debit_raw)[0] is None \
            and parse_amount(credit_raw)[0] is None:
        return True

    has_date = parse_date(date_raw) is not None
    has_debit = parse_amount(debit_raw)[0] is not None
    has_credit = parse_amount(credit_raw)[0] is not None
    has_amount = parse_amount(amount_raw)[0] is not None
    if has_date or has_debit or has_credit or has_amount:
        return False
    # Balance-only line with empty / stub narration: printed opening, not a txn.
    if STUB_NARR.match(narr):
        return True
    return False
