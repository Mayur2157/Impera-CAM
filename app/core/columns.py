"""Column band detection.

Bands come from whitespace corridors measured *only on transaction-bearing
lines*, so footer prose and secondary tables cannot destroy them. Header labels
are then mapped onto those bands to give each one a semantic name.
"""
import contextvars
import re
from .normalize import parse_amount, is_date

SYNONYMS = {
    "txn_date":   [r"^tran(saction)?\s*d(t|ate)$", r"^txn\s*d(t|ate)$", r"^trndate$",
                   r"^trans\s*date$", r"^date$", r"^post(ing)?\s*date$", r"^trans$"],
    "value_date": [r"^value\s*d(t|ate)$", r"^valuedt$", r"^val\s*dt$", r"^value$"],
    "narration":  [r"^particulars?$", r"^narration$", r"^description$", r"^remarks?$",
                   r"^transaction\s*particulars$", r"^details$"],
    "reference":  [r"^chq\.?\s*/?\s*ref\.?\s*no\.?$", r"^cheque\s*no\.?$", r"^chq\.?\s*no\.?$",
                   r"^chq$", r"^ref\s*no\.?\s*/?\s*cheque\s*no\.?$", r"^instr\.?\s*no\.?$",
                   r"^ins\s*no\s*/\s*type$", r"^insno\s*/\s*type$", r"^cheque\s*/\s*instrument$",
                   r"^tran\s*id$", r"^utr\s*number$", r"^instr\.?\s*id$", r"^cheque$",
                   r"^chq\s*/\s*ref\s*number$", r"^ref\s*no\.?$", r"^ref$"],
    "debit":      [r"^debits?$", r"^withdrawals?$", r"^withdrawals?\s*amt\.?$",
                   r"^withdrawals?\s*\(dr\)$", r"^dr$", r"^payments?$"],
    "credit":     [r"^credits?$", r"^deposits?$", r"^deposits?\s*amt\.?$",
                   r"^deposits?\s*\(cr\)$", r"^cr$", r"^receipts?$"],
    "amount":     [r"^amount$"],
    "drcr":       [r"^dr\s*/\s*cr$"],
    "balance":    [r"^(closing\s*)?balance$", r"^available\s*balance$", r"^closingbalance$",
                   r"^balance\s*\(inr\)$", r"^running\s*balance$"],
    "serial":     [r"^s\.?\s*no\.?$", r"^sl\.?\s*no\.?$", r"^sn$", r"^sr\.?\s*no\.?$"],
}
_C = {k: [re.compile(p, re.I) for p in v] for k, v in SYNONYMS.items()}
ROLE_ORDER = ["balance", "debit", "credit", "amount", "drcr", "value_date", "txn_date",
              "reference", "narration", "serial"]
HDR_HINT = re.compile(r"(date|particular|narration|description|detail|remark|withdraw|deposit|"
                      r"debit|credit|balance|chq|cheque|instrument|ref|amount|instr)", re.I)


# Word-level fallback for labels the exact list does not hold ('Transaction
# Details', 'Dr Amount', 'Withdrawal Amount', 'Debit (INR)', 'Closing Bal'):
# a label is read by the words in it, after dropping currency tags.
_CCY_RX = re.compile(r"\(?\s*(?:INR|RS\.?|₹)\s*\)?", re.I)
_W = lambda *ws: re.compile(r"\b(?:" + "|".join(ws) + r")\b", re.I)
_DEBIT_W = _W(r"withdrawals?", r"debits?", r"dr", r"payments?", r"paid\s*out")
_CREDIT_W = _W(r"deposits?", r"credits?", r"cr", r"receipts?", r"paid\s*in")
_BAL_W = _W(r"balance", r"bal")
_NARR_W = _W(r"particulars?", r"narration", r"descriptions?", r"details?", r"remarks?")
_REF_W = _W(r"chq", r"cheque", r"ref(?:erence)?", r"instr(?:ument)?", r"utr")
_DATE_W = _W(r"date", r"dt")


# every word of a column label comes from this vocabulary; anything else
# ('CASA CREDIT INTEREST', 'From Date:01-DEC-2023', 'Account Description',
# 'Total Debit Amount') is a transaction, a header field or a summary line
_LABEL_VOCAB = {
    "withdrawal", "withdrawals", "debit", "debits", "dr", "payment", "payments", "paid", "out", "in",
    "deposit", "deposits", "credit", "credits", "cr", "receipt", "receipts",
    "balance", "bal", "closing", "available", "running",
    "particular", "particulars", "narration", "description", "descriptions", "detail", "details",
    "remark", "remarks", "transaction", "transactions", "txn", "tran", "trans",
    "chq", "cheque", "ref", "reference", "instr", "instrument", "utr", "no", "number",
    "date", "dt", "value", "val", "post", "posting", "amount", "amt",
}


def _classify_words(t):
    t = _CCY_RX.sub(" ", t).strip()
    if not t or len(t) > 40 or re.search(r"\d|:", t):
        return None
    words = [w for w in re.split(r"[\s/().\-]+", t.lower()) if w]
    if not words or len(words) > 4 or any(w not in _LABEL_VOCAB for w in words):
        return None
    dr, cr = bool(_DEBIT_W.search(t)), bool(_CREDIT_W.search(t))
    if _BAL_W.search(t) and not (dr or cr):
        # 'Opening Balance' is a summary line, not a column
        return None if re.search(r"\bopening\b", t, re.I) else "balance"
    if dr and cr:
        return "drcr" if len(t.split()) <= 3 and not re.search(r"amount", t, re.I) else None
    if dr:
        return "debit"
    if cr:
        return "credit"
    if _DATE_W.search(t):
        return "value_date" if re.search(r"\bvalue\b|\bval\b", t, re.I) else "txn_date"
    if _NARR_W.search(t):
        return "narration"
    if _REF_W.search(t):
        return "reference"
    if re.fullmatch(r"(?:transaction\s*|txn\s*)?amount", t, re.I):
        return "amount"
    return None


def classify(text):
    # OCR leaves rule glyphs welded to header labels; strip them before matching
    t = re.sub(r"^[|\[\]_=~\-\s]+|[|\[\]_=~\s]+$", "", text)
    t = re.sub(r"\s+", " ", t).strip().rstrip(":").rstrip(".")
    for role in ROLE_ORDER:
        for rx in _C[role]:
            if rx.match(t):
                return role
    # the word fallback is used only when the exact labels found no table at
    # all (see extract.extract): on a layout they already read, recognising
    # header fragments changes which lines count as repeated headers
    return _classify_words(t) if WORD_FALLBACK.get() else None


# per thread / task, so one upload retrying never changes how a concurrent one is read
WORD_FALLBACK = contextvars.ContextVar("word_fallback", default=False)


def merge_cells(words, gap=6.0):
    cells = []
    for w in sorted(words, key=lambda w: w.x0):
        if cells and w.x0 - cells[-1][2] < gap:
            cells[-1] = (cells[-1][0] + " " + w.text, cells[-1][1], w.x1)
        else:
            cells.append((w.text, w.x0, w.x1))
    return cells


def header_columns(words, pad=6.0):
    """Cluster header words into columns by x-interval overlap, across all lines
    of the header block, then read each column top-to-bottom."""
    iv = sorted(((w.x0, w.x1, w.top, w.text) for w in words), key=lambda t: t[0])
    cols = []
    for x0, x1, top, txt in iv:
        if cols and x0 <= cols[-1]["x1"] + pad:
            cols[-1]["x1"] = max(cols[-1]["x1"], x1)
            cols[-1]["w"].append((top, x0, txt))
            cols[-1]["words"].append((txt, x0, x1))
        else:
            cols.append({"x0": x0, "x1": x1, "w": [(top, x0, txt)],
                         "words": [(txt, x0, x1)]})
    out = []
    for c in cols:
        toks = sorted(c["w"])
        words = [(t, x, x) for _, x, t in toks]
        names = [t for _, _, t in toks]
        ded = [t for i, t in enumerate(names)
               if i == 0 or t.lower() != names[i - 1].lower()]
        out.append((" ".join(ded), c["x0"], c["x1"], c["words"]))
    return out


def _roles_from_words(words, split_welded=False):
    roles = {}

    def put(role, x0, x1):
        key, n = role, 2
        while key in roles:                 # Kotak prints 'Dr / Cr' twice
            key = f"{role}_{n}"; n += 1
        roles[key] = (x0, x1)

    for txt, x0, x1, parts in header_columns(words):
        r = classify(txt)
        if r:
            put(r, x0, x1)
            continue
        if not split_welded:
            continue
        # OCR sometimes welds neighbouring headers into one box
        # ('No. Withdrawals Deposits'). Recover them word by word, each keeping
        # its own x range. Only done for OCR'd pages: on a digital page a
        # multi-word label is real and splitting it corrupts the bands.
        for t, wx0, wx1 in parts:
            rr = classify(t)
            if rr:
                put(rr, wx0, wx1)
    return roles


def find_header(lines, ocr=False):
    """Try each line alone, then merged with the next (2-line headers are common:
    'TXN / DATE', 'Ref No./Cheque / No.'). Keep the richest interpretation."""
    best = None
    for i, ln in enumerate(lines[:250]):
        if not HDR_HINT.search(ln.text()):
            continue
        cands = [(i, i, ln.words)]
        if i + 1 < len(lines) and lines[i + 1].top - ln.top < 22 \
                and HDR_HINT.search(lines[i + 1].text()):
            cands.append((i, i + 1, ln.words + lines[i + 1].words))
        for start_i, end_i, ws in cands:
            roles = _roles_from_words(ws, split_welded=ocr)
            has_money = ("balance" in roles) and (
                {"debit", "credit"} & roles.keys() or "amount" in roles)
            if not has_money:
                continue
            score = len(roles) + (2 if {"debit", "credit"} <= roles.keys() else 0)
            if best is None or score > best[0]:
                best = (score, start_i, end_i, roles)
    if best is None:
        return None, None
    return (best[1], best[2]), best[3]



def txn_lines(lines):
    """Lines carrying >=2 money tokens, or 1 money token plus a date. These define
    the table's true geometry; footers and side tables do not."""
    out = []
    for ln in lines:
        money = date = 0
        for w in ln.words:
            if parse_amount(w.text)[0] is not None and not is_date(w.text):
                money += 1
            elif is_date(w.text):
                date += 1
        if money >= 2 or (money >= 1 and date >= 1):
            out.append(ln)
    return out


def corridors(lines, page_width, step=0.5, tol_frac=0.08, min_gap=2.5):
    """Coverage histogram over x; runs of near-zero coverage are separators."""
    if not lines:
        return []
    n = int(page_width / step) + 2
    cov = [0] * n
    for ln in lines:
        hit = set()
        for w in ln.words:
            a, b = int(w.x0 / step), min(int(w.x1 / step) + 1, n - 1)
            for k in range(a, b + 1):
                hit.add(k)
        for k in hit:
            cov[k] += 1
    thresh = max(0, int(len(lines) * tol_frac))
    gaps, run = [], None
    for k in range(n):
        if cov[k] <= thresh:
            run = k if run is None else run
        else:
            if run is not None and (k - run) * step >= min_gap:
                gaps.append((run * step, k * step))
            run = None
    if run is not None and (n - run) * step >= min_gap:
        gaps.append((run * step, n * step))
    return gaps


def ink_runs(gaps, lo, hi):
    """Complement of the corridors: the x ranges where the table actually prints."""
    runs, cur = [], lo
    for g0, g1 in sorted(gaps):
        if g1 <= lo or g0 >= hi:
            continue
        if g0 > cur:
            runs.append((cur, min(g0, hi)))
        cur = max(cur, g1)
    if cur < hi:
        runs.append((cur, hi))
    return [r for r in runs if r[1] - r[0] > 0.5]


def _nearest_run(interval, runs, name=None):
    a, b = interval
    # For amount columns (debit/credit), right-aligned amounts do not finish
    # strictly to the left of their column header (x1 < a - 8).
    if name and _role_base(name) in ("debit", "credit"):
        cands = [i for i, (x0, x1) in enumerate(runs) if x1 >= a - 8]
        if not cands:
            cands = list(range(len(runs)))
    else:
        cands = list(range(len(runs)))
    best, bd = cands[0], None
    for i in cands:
        x0, x1 = runs[i]
        d = 0.0 if (a < x1 and b > x0) else min(abs(a - x1), abs(x0 - b))
        if bd is None or d < bd:
            best, bd = i, d
    return best


def _role_base(name):
    m = re.match(r"^(.*)_(\d+)$", name)
    return m.group(1) if m else name


def _shared_run_edge(left_name, left_box, right_name, right_box, run):
    """Split two headers that mapped onto the same ink run.

    Default is the midpoint of the two labels (adjacent amount columns). When
    the left header is Description and the right is Instr/Ref, and the right
    label sits *past* the ink, the run is wrapped narration filling a wide
    field — splitting at the midpoint would steal LTD/FINANCE/BU into
    Reference. Give Description the whole run and start Instr at its header.
    """
    left_x1, right_x0 = left_box[1], right_box[0]
    run_x1 = run[1]
    if (_role_base(left_name) == "narration"
            and _role_base(right_name) == "reference"
            and right_x0 >= run_x1 - 8):
        return float(right_x0)
    if (_role_base(left_name) == "txn_date"
            and _role_base(right_name) == "narration"):
        if run_x1 < right_x0 and run_x1 < (left_x1 + right_x0) / 2.0:
            return float(run_x1 + 3.0)
    return (left_x1 + right_x0) / 2.0


def build_bands(roles, body_lines, page_width):
    """Edges land on the corridor between two columns' ink runs. When two header
    labels share one ink run (adjacent amount columns with no visible gap, or an
    entirely empty column) the split falls back to the header-label midpoint,
    except Description/Instr No. where the instrument column is sparse."""
    ordered = sorted(roles.items(), key=lambda kv: kv[1][0])
    src = txn_lines(body_lines) or body_lines
    gaps = corridors(src, page_width)
    ink = [(w.x0, w.x1) for ln in src for w in ln.words]
    if not ink:
        return {n: (0.0, page_width) for n, _ in ordered}
    lo_ink, hi_ink = min(a for a, _ in ink), max(b for _, b in ink)
    runs = ink_runs(gaps, lo_ink, hi_ink) or [(lo_ink, hi_ink)]
    idx = [_nearest_run(r[1], runs, r[0]) for r in ordered]

    edges = [0.0]
    for i in range(len(ordered) - 1):
        ia, ib = idx[i], idx[i + 1]
        name_a, box_a = ordered[i]
        name_b, box_b = ordered[i + 1]
        if ib > ia:
            e = (runs[ib - 1][1] + runs[ib][0]) / 2.0
        else:
            e = _shared_run_edge(name_a, box_a,
                                 name_b, box_b,
                                 runs[ia])
        if _role_base(name_b) == "reference" and box_b[0] < e and box_b[0] >= runs[ib - 1][1]:
            e = box_b[0]
        if name_b == "balance" and e < box_b[0] and runs[ib][0] >= box_b[0]:
            e = box_b[0]
        edges.append(max(e, edges[-1] + 1))
    edges.append(max(page_width + 60, edges[-1] + 1))
    bands = {name: (edges[i], edges[i + 1]) for i, (name, _) in enumerate(ordered)}
    bands["_ink_runs"] = {ordered[i][0]: runs[idx[i]] for i in range(len(ordered))}
    return bands
