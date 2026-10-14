"""Decide whether a page carries a usable text layer or has to be OCR'd.

A statement PDF is almost never uniformly one or the other: banks routinely
staple a scanned first page onto a digitally generated table, or vice versa.
So the decision is made per page, not per document.
"""
from dataclasses import dataclass

import re

MIN_CHARS = 40          # below this a page is effectively blank of text
MIN_ALNUM_RATIO = 0.50  # broken CID encodings produce mostly punctuation
MIN_DIGIT_HITS = 4      # a transaction page always prints several numbers
STRONG_DIGITS = 20      # plenty of numbers plus words means a real text layer
STRONG_LETTERS = 40

# Plain-text statements (Cosmos, JPCB) rule their columns with long runs of
# '-' or '='. Those are layout, not evidence of a broken text layer, so they
# are stripped before the alphanumeric ratio is measured.
_RULE_RUN = re.compile(r"(.)\1{2,}")


@dataclass
class PageKind:
    page: int
    scanned: bool
    chars: int
    reason: str


def classify_page(page, pageno: int) -> PageKind:
    chars = page.chars or []
    n = len(chars)
    if n < MIN_CHARS:
        return PageKind(pageno, True, n, "no text layer")

    text = "".join(c.get("text", "") for c in chars)
    digits = sum(1 for ch in text if ch.isdigit())
    letters = sum(1 for ch in text if ch.isalpha())
    if digits >= STRONG_DIGITS and letters >= STRONG_LETTERS:
        return PageKind(pageno, False, n, "digital")

    cleaned = _RULE_RUN.sub(lambda m: m.group(1) if m.group(1).isalnum() else "", text)
    alnum = sum(1 for ch in cleaned if ch.isalnum())
    if alnum / max(1, len(cleaned)) < MIN_ALNUM_RATIO:
        return PageKind(pageno, True, n, "text layer is mostly non-alphanumeric")

    if digits < MIN_DIGIT_HITS:
        return PageKind(pageno, True, n, "text layer carries almost no digits")

    return PageKind(pageno, False, n, "digital")


def classify_document(pdf):
    return [classify_page(p, i) for i, p in enumerate(pdf.pages, 1)]
