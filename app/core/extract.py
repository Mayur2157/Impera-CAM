"""PDF -> transactions. Bands are pooled over the whole document; the balance
chain picks the row-assembly strategy."""
import re
import pdfplumber
from .layout import page_words, to_lines
from .columns import find_header, build_bands
from .rows import (blocks_by_gap, blocks_by_balance, blocks_by_date,
                  block_to_row, is_noise_row, cells_of, _has_balance,
                  rehome_chq_tail, rehome_interest_rows, polish_row, TXN_HEAD_RX)
from .normalize import parse_amount, parse_date, complete_partial_date, is_date
from .validate import chain_score, reconstruct
from .classify import classify_page
from . import ocr as ocr_mod
from .clean import (is_chrome_line, repeated_line_keys, scrub_field,
                    is_stub_row, looks_like_footer)

YEAR_WRAP = re.compile(r"^(?:19|20)\d{2}$")

STRATS = {"gap": blocks_by_gap, "bal": blocks_by_balance, "date": blocks_by_date}

TERMINATOR = re.compile(
    r"^\s*(grand\s*total|sub\s*total|page\s*total|total\s*[:\-]|totals?\s*/?\s*balance|closing\s*balance|"
    r"#\s*entries|statement\s*summary|summary\s*of|total\s+\d)", re.I)


LABELLED = re.compile(r"[A-Za-z]\s*[:\-]{1,2}\s*\S")


def trim_continuation(lines, ref):
    """Some banks (HDFC) reprint the account box on every page but the column
    header only once. Without the header to cut at, that box would be parsed as
    transactions -- a customer id lands in the debit column and the balance
    chain snaps at every page break. Continuation pages therefore start at the
    first line carrying a balance, walking back only over unlabelled lines,
    which is what a wrapped narration from the previous page looks like."""
    from .rows import cells_of
    if not lines:
        return lines
    bands = {"balance": ref["balance"]} if "balance" in ref else None
    lo, hi = (bands["balance"] if bands else (0, 0))
    first = None
    for i, ln in enumerate(lines):
        for w in ln.words:
            if lo - 40 <= w.mid and parse_amount(w.text)[0] is not None \
                    and w.mid >= lo - 40:
                first = i
                break
        if first is not None:
            break
    if first is None:
        return lines
    start = first
    while start > 0 and first - start < 4:
        prev = lines[start - 1]
        if LABELLED.search(prev.text()):
            break
        start -= 1
    return lines[start:]


def compatible(roles, ref):
    return roles and ref and "balance" in roles and len(set(roles) & set(ref)) >= 3


def words_for_page(page, pageno, use_ocr=True, dpi=300, backend=None, report=None):
    """One entry point for both page kinds. Scanned pages go through OCR and come
    back as the same Word objects, so nothing downstream needs to know."""
    kind = classify_page(page, pageno)
    if report is not None:
        report.append(kind)
    if not kind.scanned:
        return page_words(page, pageno)
    if not use_ocr:
        return []
    try:
        return ocr_mod.ocr_page_words(page, pageno, dpi=dpi, backend=backend)
    except ocr_mod.OCRUnavailable:
        # No engine installed. Fall back to whatever text layer exists rather
        # than dropping the page: a partial read beats silently losing rows.
        if report:
            report[-1].reason += " (no OCR engine, used text layer)"
        return page_words(page, pageno)


def collect(pdf, use_ocr=True, dpi=300, backend=None, report=None):
    """Returns (ref_roles, [(page_no, body_lines, width)], header_top). The table
    closes at a terminator and only reopens when a compatible header reappears."""
    ref, pages, active, htop = None, [], False, None
    for i, page in enumerate(pdf.pages, 1):
        lines = to_lines(words_for_page(page, i, use_ocr, dpi, backend, report))
        if not lines:
            continue
        was_ocr = bool(report) and report[-1].scanned
        hdr_range, roles = find_header(lines, ocr=was_ocr)
        if roles is not None and (ref is None or compatible(roles, ref)):
            h_start, h_end = hdr_range
            if ref is None:
                ref = roles
                if i == 1:
                    htop = lines[h_end].top
            else:
                if h_start > 0 and active:
                    term_idx = None
                    for j, ln in enumerate(lines[:h_start]):
                        if TERMINATOR.match(ln.text()):
                            term_idx = j
                            break
                    if term_idx is not None and term_idx > 0:
                        pre_body = trim_continuation(lines[:term_idx], ref)
                        pre_body = [l for l in pre_body if l.text().strip().lower() != "untitled"]
                        if pre_body:
                            pages.append((i, pre_body, page.width))
            body, active = lines[h_end + 1:], True
        elif active:
            body = trim_continuation(lines, ref)           # header printed once only
        else:
            continue
        cut = len(body)
        for j, ln in enumerate(body):
            if TERMINATOR.match(ln.text()):
                cut = j
                active = False
                break
        if cut:
            pages.append((i, body[:cut], page.width))
    return ref, pages, htop


def strip_chrome(pages, bands):
    """Drop page-footer / disclaimer / rule lines before row assembly.

    Balance-bearing lines are never dropped — a real last-of-page posting must
    stay even if the bank prints a disclaimer in the same column underneath.
    Non-balance lines that match a footer phrase, or that repeat across pages,
    are chrome and would otherwise glue onto the last transaction.
    """
    page_texts = []
    for _, body, _ in pages:
        texts = []
        for ln in body:
            if _has_balance(cells_of(ln, bands)):
                continue
            texts.append(ln.text())
        page_texts.append(texts)
    repeats = repeated_line_keys(page_texts)
    out = []
    for pno, body, width in pages:
        kept = []
        for ln in body:
            # Page markers / disclaimer lines can carry a digit that lands in
            # the balance band ('Page 1' → balance=1). Drop them even then.
            if looks_like_footer(ln.text()):
                continue
            if _has_balance(cells_of(ln, bands)) or not is_chrome_line(ln.text(), repeats):
                kept.append(ln)
        if kept:
            out.append((pno, kept, width))
    return out


def _is_year_wrap_line(ln, bands):
    """'2023' in the date column with no amounts — Bandhan/SBI year wrap."""
    c = cells_of(ln, bands)
    if _has_balance(c):
        return False
    d = (c.get("txn_date") or "").strip()
    return bool(YEAR_WRAP.match(d))


def _is_page_break_wrap_line(ln, bands):
    """Continuation of the previous page's last posting.

    Bandhan: year wrap. HDFC: leftover UTR ``RATNR52019100400464381``.
    A new txn start (Canara UPI/CR) or a VPA wrap stays on this page.
    """
    if _is_year_wrap_line(ln, bands):
        return True
    c = cells_of(ln, bands)
    if _has_balance(c) or is_date(c.get("txn_date") or ""):
        return False
    narr = (c.get("narration") or ln.text() or "").strip()
    ref = (c.get("reference") or "").strip()
    if TXN_HEAD_RX.match(narr) or "/" in narr or "@" in narr:
        return False
    blob = re.sub(r"\s+", "", narr or ref)
    return bool(re.fullmatch(r"[A-Za-z0-9]{10,}", blob))


def rehome_page_break_wraps(pages, bands):
    """Move a year+UTR wrap at the top of page N onto the last row of page N-1.

    Bandhan prints ``05-DEC-`` + amounts at the bottom of a page and
    ``2023  2700EC…`` at the top of the next. Without this, the wrap becomes
    the next transaction's narration and the date stays incomplete.
    """
    out = [(p, list(body), w) for p, body, w in pages]
    for i in range(1, len(out)):
        pno, body, width = out[i]
        k = 0
        while k < len(body) and _is_page_break_wrap_line(body[k], bands):
            k += 1
        if k and out[i - 1][1]:
            prev_p, prev_body, prev_w = out[i - 1]
            out[i - 1] = (prev_p, prev_body + body[:k], prev_w)
            out[i] = (pno, body[k:], width)
    return [(p, b, w) for p, b, w in out if b]


def rows_to_txns(rows, bands):
    rows = rehome_chq_tail(list(rows))
    rows = rehome_interest_rows(rows)
    for r in rows:
        polish_row(r)
    out = []
    for r in rows:
        if is_noise_row(r) or is_stub_row(r):
            continue
        bal, bflag = parse_amount(r.get("balance", ""))
        if bal is None:
            continue
        if bflag == "DR" and bal > 0:
            bal = -bal
        if "amount" in bands:                              # single amount + Dr/Cr flag
            amt, af = parse_amount(r.get("amount", ""))
            flag = (r.get("drcr") or af or "").strip().upper()
            d = amt if flag.startswith("D") else None
            c = amt if flag.startswith("C") else None
        else:
            d, _ = parse_amount(r.get("debit", ""))
            c, _ = parse_amount(r.get("credit", ""))
        if d == 0: d = None
        if c == 0: c = None
        # A negative withdrawal is money coming back (Canara prints a UPI
        # reversal as '-60.00' under Withdrawals): it belongs in the other
        # column. The running balance is unchanged either way.
        if d is not None and d < 0 and c is None:
            d, c = None, -d
        elif c is not None and c < 0 and d is None:
            d, c = -c, None
        raw_d, raw_v = r.get("txn_date", "") or "", r.get("value_date", "") or ""
        out.append({
            "txn_date": parse_date(raw_d),
            "value_date": parse_date(raw_v),
            "_date_raw": raw_d,
            "_value_raw": raw_v,
            "narration": scrub_field(r.get("narration")),
            "reference": scrub_field(r.get("reference")),
            "debit": d, "credit": c, "balance": bal, "page": r["_page"],
            "_raw_lines": r.get("_raw_lines", []),
        })
    return fill_missing_dates(out)


def fill_missing_dates(txns):
    """Bandhan '05-DEC-' and SBI '14 Oct' wrap the year onto another line.
    Borrow the year from the nearest dated neighbour."""
    def neighbor_year(i):
        for j in range(i - 1, -1, -1):
            if txns[j].get("txn_date"):
                return txns[j]["txn_date"].year
        for j in range(i + 1, len(txns)):
            if txns[j].get("txn_date"):
                return txns[j]["txn_date"].year
        return None

    # Some banks print the date only on the first row of each day (Standard
    # Chartered): a row whose date cell is empty belongs to the day above it.
    # Only an EMPTY date cell is filled; an unreadable one is left alone.
    for i, t in enumerate(txns):
        if t.get("txn_date") is None and not (t.get("_date_raw") or "").strip() and i > 0 \
                and txns[i - 1].get("txn_date"):
            t["txn_date"] = txns[i - 1]["txn_date"]
            if t.get("value_date") is None and not (t.get("_value_raw") or "").strip():
                t["value_date"] = txns[i - 1].get("value_date")
    for i, t in enumerate(txns):
        y = neighbor_year(i)
        if not y:
            continue
        if t.get("txn_date") is None:
            t["txn_date"] = complete_partial_date(t.get("_date_raw") or "", y)
        # A value date the PDF does not print stays blank; copying the txn date
        # would invent one (Kotak prints none except '(Value Date:…)' notes).
        if t.get("value_date") is None:
            t["value_date"] = complete_partial_date(t.get("_value_raw") or "", y)
    return txns


def extract(path, password=None, use_ocr=True, dpi=300, backend=None):
    """Exact column labels first. Only if they find no transaction table is
    the page read again with word-level label matching ('Dr Amount',
    'Transaction Details'), so layouts the exact labels read never change."""
    result = _extract(path, password, use_ocr, dpi, backend)
    if result[1][3]:
        return result
    from . import columns
    token = columns.WORD_FALLBACK.set(True)
    try:
        retry = _extract(path, password, use_ocr, dpi, backend)
    finally:
        columns.WORD_FALLBACK.reset(token)
    if retry[1][3]:
        retry[2]["_word_fallback"] = True          # read with word-level header labels
        return retry
    return result


def _extract(path, password=None, use_ocr=True, dpi=300, backend=None):
    report = []
    with pdfplumber.open(path, password=password) as pdf:
        ref, pages, htop = collect(pdf, use_ocr, dpi, backend, report)
        if not ref or not pages:
            return None, (0.0, 0, "asis", []), {}, htop, report
        pooled = [ln for _, body, _ in pages for ln in body]
        width = max(w for _, _, w in pages)
        bands = build_bands(ref, pooled, width)
        pages = strip_chrome(pages, bands)
        pages = rehome_page_break_wraps(pages, bands)
        results = {}
        for name, fn in STRATS.items():
            rows = []
            for _, body, _ in pages:
                for blk in fn(body, bands):
                    rows.append(block_to_row(blk, bands))
            txns = rows_to_txns(rows, bands)
            results[name] = (*chain_score(txns), txns)
    # Ties are common because several strategies can produce a perfect chain.
    # Break them toward the principled one: balance-anchoring handles wrapped
    # narration correctly, date-anchoring only happens to agree on simple tables.
    PREF = {"bal": 3, "gap": 2, "date": 1}
    best = max(results.items(),
               key=lambda kv: (round(kv[1][0], 6), kv[1][1], PREF[kv[0]]))
    return best[0], best[1], results, htop, report
