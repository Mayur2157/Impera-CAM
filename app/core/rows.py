"""Row assembly. Three competing strategies; the balance chain picks the winner."""
import re, statistics
from .normalize import (parse_amount, parse_date, is_date, date_extra,
                        looks_like_date_fragment)

NOISE_RX = re.compile(
    r"(grand\s*total|sub\s*total|page\s*total|^totals?\b|totals?\s*/?\s*balance|carried\s*forward|brought\s*forward|"
    r"\bbalance\s*(?:b/?f|c/?f|forward|brought|carried)\b|"
    r"\b[cb]\s*/\s*f\b|\b[cb]\.[-\s]*f\.\b|continued|closing\s*balance|opening\s*balance|statement\s*of|"
    r"^page\s*(no\.?)?\s*\d|disclaimer|generated\s*on|this\s*is\s*a\s*(computer|system))", re.I)


def _is_ref_role(name):
    return name == "reference" or (name.startswith("reference_") and name[10:].isdigit())


def looks_like_instrument(text):
    """Cheque / UTR / IMPS / NEFT ids are digit-heavy or mixed codes.

    Pure letter fragments (FINANCE, LIMITED, TRANSFER, P) that land in the
    Instr/Ref column are description overflow, not instruments. 3-digit
    cheque numbers (Kotak 108) are instruments; a lone 'T' type code is not
    handled here — `_word_role` keeps it in Reference separately.
    """
    t = re.sub(r"[^A-Za-z0-9]", "", text or "")
    if not t:
        return False
    digits = sum(c.isdigit() for c in t)
    letters = sum(c.isalpha() for c in t)
    if digits >= 3 and letters == 0:
        return True
    if digits >= 4:
        return True
    if digits >= 2 and letters >= 1 and len(t) >= 8:
        return True
    if digits >= 1 and letters >= 1 and len(t) >= 10:
        return True
    return False


_AMOUNT_FLAG = re.compile(r"^(cr|dr)$", re.I)


def _continues_description(w, bands, line):
    """True when `w` is narration text that ran past the Description column:
    walking left along its line, every gap is no wider than a word space
    until a word printed in Description is reached ('RELIGARE FINVEST' +
    'LTD BU' running into Instr). A word that starts after a column gap
    (SBI's 'TRANSFER', 67pt after the description) is the next column's."""
    nbox = bands.get("narration")
    if not nbox or line is None:
        return False
    words = sorted(line.words, key=lambda x: x.x0)
    try:
        k = next(i for i, x in enumerate(words) if x is w)
    except StopIteration:
        return False
    space = 0.6 * max(1.0, w.bottom - w.top)
    while k > 0:
        prev, cur = words[k - 1], words[k]
        if cur.x0 - prev.x1 > space:
            return False
        if nbox[0] <= prev.mid < nbox[1]:
            return True
        k -= 1
    return False


def _word_role(w, bands, line=None):
    """Assign a word to a column. Where a word is printed decides first; its
    text only refines that, never overrides it without evidence.

    A word in a reference column is narration overflow only when the
    evidence says so: it starts inside Description, or it continues a
    description word with no column gap (`_continues_description`). Plain
    words printed in the Ref column after a gap stay there (SBI prints
    'TRANSFER TO <account>' in its Ref No. cell, clipped to 'TRANSFER T').

    Other cases:
    - tokens in UTR / Instr. ID (reference_2+) including Union 'Sender'
    - day/month/year fragments in the date band (SBI '1 Sep 2020')
    - non-numeric words that leaked into Debit (Bandhan 'APY TO')
    """
    assigned = None
    for name, band in bands.items():
        if name.startswith("_") or not isinstance(band, (tuple, list)):
            continue
        lo, hi = band
        if lo <= w.mid < hi:
            assigned = name
            break
    if assigned and _is_ref_role(assigned):
        if not looks_like_instrument(w.text):
            nbox = bands.get("narration")
            if nbox and nbox[0] <= w.x0 < nbox[1]:
                return "narration"          # starts inside Description
        if assigned != "reference":
            return assigned
        if not looks_like_instrument(w.text) and _continues_description(w, bands, line):
            return "narration"              # runs on from a description word
        return assigned
    if assigned in ("txn_date", "value_date") and not looks_like_date_fragment(w.text):
        return "narration"
    if assigned in ("debit", "credit", "amount", "balance"):
        if parse_amount(w.text)[0] is None and not _AMOUNT_FLAG.match(w.text.strip()):
            return "narration"
    return assigned


def cells_of(line, bands):
    out = {k: [] for k in bands}
    for w in line.words:
        name = _word_role(w, bands, line)
        if name:
            out[name].append(w)
    return {k: " ".join(x.text for x in sorted(v, key=lambda w: w.x0)) for k, v in out.items()}


def _has_balance(cells):
    v, _ = parse_amount(cells.get("balance", ""))
    return v is not None


def _has_txn_date_ink(line, bands):
    lo, hi = bands.get("txn_date", (None, None))
    if lo is None:
        return False
    return any(lo <= w.mid < hi for w in line.words)


def join_cell(parts):
    out = ""
    for p in parts:
        if not p:
            continue
        if not out:
            out = p
        elif out.endswith("-") or out.endswith("/") or _midword_wrap(out, p):
            out += p
        else:
            out += " " + p
    return out.strip()


def _letter_run_end(s):
    i = len(s)
    while i > 0 and s[i - 1].isalpha():
        i -= 1
    return s[i:]


def _letter_run_start(s):
    i = 0
    while i < len(s) and s[i].isalpha():
        i += 1
    return s[:i]


def _midword_wrap(prev, nxt):
    """Column-clipped words: ULTRAT+ECH, CUTTIN+G, PA+YMENT, CENTUR+Y, L+TD.

    Do not glue complete words (STAR + BAZA, MAHESH + MA, INB + IMPS).
    """
    if not prev or not nxt:
        return False
    if not prev[-1].isalpha() or not nxt[0].isalpha():
        return False
    tail, head = _letter_run_end(prev), _letter_run_start(nxt)
    rest = nxt[len(head):]
    prefix = prev[:len(prev) - len(tail)]

    # one leftover letter from a wrap (CUTTIN+G, CENTUR+Y, CONTAINE+R)
    if len(head) == 1 and len(tail) >= 3:
        return True
    # PVT L + TD → LTD (single letter left on the previous line)
    if len(tail) == 1 and len(head) == 2:
        return True
    # MA/SBIN is a new path component, not the rest of MAHESH
    if len(head) >= 2 and rest.startswith("/"):
        return False
    if not (prefix.endswith("/") or prefix.endswith("-")):
        return False
    # /ULTRAT + ECH
    if len(tail) >= 4 and 1 <= len(head) <= 3:
        return True
    # /PA + YMENT — not /REX + POLYEXTRUSION (a new complete word)
    if 1 <= len(tail) <= 2 and 3 <= len(head) <= 6:
        return True
    return False


# Short words that start a new word, never finish a clipped one ('VASA STEEL' + 'AND ALLOYS')
_WHOLE_SHORT_WORDS = {"AND", "OF", "THE", "CO", "LTD", "PVT", "INC", "LLP", "FOR", "TO", "BY", "AT", "IN", "ON", "A"}


def _clip_suffix(prev, nxt):
    """Line hit the column edge: MULTIMOD+AL. Do not glue /REX + POLYEXTRUSION."""
    if not prev or not nxt or not prev[-1].isalpha() or not nxt[0].isalpha():
        return False
    head, tail = _letter_run_start(nxt), _letter_run_end(prev)
    if nxt[len(head):].startswith("/"):
        return False
    if head.upper() in _WHOLE_SHORT_WORDS and not nxt[len(head):len(head) + 1].isalnum():
        return False
    return 1 <= len(head) <= 3 and len(tail) >= 4


def _digit_clip_wrap(prev, nxt):
    """Column-clipped VPA / UPI id: igpgopay1.088 + 830@ic, jiteshkumar66 + 79@axl.

    A complete date followed by a time is two fields, not one clipped number
    ('…/24/06/2024' + '09:14:21')."""
    if not prev or not nxt:
        return False
    if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}$", prev) and re.match(r"\d{1,2}:\d{2}", nxt):
        return False
    return prev[-1].isdigit() and nxt[0].isdigit()


def _ref_clip_wrap(prev, nxt):
    """A reference code split by column width: the tail that spilled onto the
    next line is pure digits -- the bank simply ran out of room mid-number
    (HDFC 'RATNR52019100400' + '464381', Union 'No:KKBKNR2011' + '070097').

    A second, complete alphanumeric code that merely starts with a digit
    (SBI 'IMPS0001824311' + '9MOADJSZVZ9') is a distinct reference sitting on
    the next line, not a wrapped tail, and must stay space-separated.
    """
    if not prev or not nxt:
        return False
    return prev[-1].isdigit() and nxt.isdigit()


def _vpa_wrap(prev, nxt):
    """Clipped UPI VPA: bunty.srt@ybl+/Payme, 9162895977@+ybl/Paym, @yb+l/Payme.

    A following UPI/IMPS/NEFT line is the next transaction, not a handle wrap.
    """
    if not prev or not nxt:
        return False
    if nxt.upper().startswith(("UPI/", "IMPS/", "NEFT/", "RTGS/", "NACH", "ECS")):
        return False
    last = prev.rsplit("/", 1)[-1]
    if "@" not in last:
        return False
    domain = last.rsplit("@", 1)[1]
    if domain == "":
        return nxt[:1].isalpha()
    if nxt[:1] in "/-":
        return False
    return nxt[:1].isalpha()


def _geom_role(w, bands):
    """Column by midpoint only — no overflow reclassification."""
    for name, band in bands.items():
        if name.startswith("_") or not isinstance(band, (tuple, list)):
            continue
        lo, hi = band
        if lo <= w.mid < hi:
            return name
    return None


def _hash_wrap(prev, nxt):
    """A column-clipped UPI/payment hash split across lines.

    Canara: '…CUTTING//PTM5E3C4FF95EA24E478A9' + 'F92D06C0E6935/…'
    Bandhan: 'UPI/DR/…/HDF6F2E' + 'ACBBA3BB476CBB3EBAE17F'

    Both pieces are long alphanumeric tokens (digits + letters, ≥ 4 chars
    each). A plain English word following a narration (e.g. MAHESH + MA/SBIN)
    does NOT trigger this because the head piece starts a UPI path with '/'.
    """
    if not prev or not nxt:
        return False
    tail = prev.rsplit("/", 1)[-1] if "/" in prev.split()[-1] else prev.split()[-1]
    head = nxt.split("/", 1)[0] if "/" in nxt.split()[0] else nxt.split()[0]
    if not (re.fullmatch(r"[A-Za-z0-9]{4,}", tail) and re.fullmatch(r"[A-Za-z0-9]{4,}", head)):
        return False

    # A payment hash is hex behind an optional 3-letter bank prefix (HDF, PTM,
    # YBL, AXI, IBL). Both pieces must look like that; a letter/digit change at
    # the break between a word and a number ('KCCBN19124935567' + 'BHAIRAV',
    # 'INTERNATI' + '0112966287') is two tokens and keeps its space.
    def hexish(s, prefix_ok):
        body = s[3:] if prefix_ok and re.match(r"[A-Z]{3}", s) and len(s) > 3 else s
        return bool(re.fullmatch(r"[0-9A-F]+", body.upper()))

    def mixed(s):
        return any(c.isdigit() for c in s) and any(c.isalpha() for c in s)
    combined = tail + head
    if len(combined) < 12 or not mixed(combined):
        return False
    # base-36 hashes mix letters and digits on both sides ('HMGZTFE8L06Y' + 'DHHGK3BYXW64P')
    return (mixed(tail) and mixed(head)) or (hexish(tail, True) and hexish(head, False))


def _upi_handle_wrap(prev, nxt):
    """BoB prints the VPA right after '/UPI/'; a VPA never holds a space, so a
    clipped one continues on the next line: 'UPI/…/UPI/krishnandank' + 'umar988'."""
    if not prev or not nxt:
        return False
    return bool(re.search(r"/UPI/[A-Za-z0-9._\-]+$", prev) and re.match(r"[A-Za-z0-9._\-]+(?:@|/|$)", nxt))


def _date_wrap(prev, nxt):
    """A column-clipped partial date: '…27/06/20' + '24 10:51:35'."""
    if not prev or not nxt:
        return False
    tail = prev.split()[-1]
    head = nxt.split()[0]
    return bool(re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2}$", tail)
                and re.match(r"^\d{2}\b", head))


def _sublines(words, y_tol=2.5):
    """One logical line can hold two stacked narration lines (Canara prints the
    amounts level with a two-line hash '…0244859A0A' / '70B01EB8…'). Split them
    by print height so the wrap rules see each physical line separately."""
    rows = []
    for w in sorted(words, key=lambda w: w.top):
        if rows and abs(w.top - rows[-1][0].top) <= y_tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w.x0) for r in rows]


def _ref_has_from(block, bands):
    """SBI BY TRANSFER prints a 3-line Ref cell: TRANSFER / FROM / <account>."""
    rbox = bands.get("reference")
    if not rbox:
        return False
    return any(
        rbox[0] <= w.mid < rbox[1] and w.text.strip().upper() == "FROM"
        for ln in block for w in ln.words
    )


def join_narration(block, bands):
    """Keep the full description: join wrapped lines, gluing mid-word clips.

    Words whose midpoint sits in the Ref column stay out of the description
    when that column is a stacked TRANSFER/FROM/<account> cell (SBI BY
    TRANSFER). Otherwise letter overflow from a clipped description into Ref
    (XXXX644KVBL- TRANSFER) is still kept.

    Rule 3: If the first line fills the column to its right (ink-run) edge and
    neither piece has a space at the break, join with no space.  This handles
    Canara/Bandhan UPI hash splits and partial dates without adding a spurious
    space inside tokens while still keeping word-boundary wraps space-separated.
    """
    nbox = bands.get("narration")
    if not nbox:
        return join_cell([cells_of(ln, bands).get("narration") or "" for ln in block])
    lo, hi = nbox
    # Use the actual ink-run right edge for the column-clip test; it is tighter
    # than the band edge (which extends to the next column's start).
    ink_run = bands.get("_ink_runs", {}).get("narration")
    col_hi = ink_run[1] if ink_run else hi
    skip_ref = _ref_has_from(block, bands)
    segments = []
    for ln in block:
        words = []
        for w in sorted(ln.words, key=lambda w: w.x0):
            geom = _geom_role(w, bands)
            if skip_ref and _is_ref_role(geom or ""):
                continue
            if _word_role(w, bands, ln) != "narration":
                continue
            words.append(w)
        segments.extend(_sublines(words))
    out, prev_clip = "", False
    for words in segments:
        text = " ".join(w.text for w in words)
        # Clipped when the last word's right edge reaches the ink-run boundary.
        clipped = words[-1].x1 >= col_hi - 8
        if not out:
            out = text
        elif out.endswith("/"):
            out += text
        elif out.endswith("-"):
            # 'BY TRANSFER-' + 'NEFT*' glues; a clipped UTR '-' + company name
            # must not weld into HDFCR…40-VIGNESH.
            if prev_clip and len(out) >= 2 and out[-2].isdigit() and text[:1].isalpha():
                out += " " + text
            else:
                out += text
        elif _midword_wrap(out, text) or _vpa_wrap(out, text):
            out += text
        elif prev_clip and (text[:1] in "/-" or _clip_suffix(out, text)
                            or _digit_clip_wrap(out, text)):
            out += text
        elif prev_clip and (_hash_wrap(out, text) or _date_wrap(out, text) or _upi_handle_wrap(out, text)):
            # Rule 3: column-clipped hash / partial date — glue with no space.
            out += text
        else:
            out += " " + text
        prev_clip = clipped
    return out.strip()


def join_ref_band(block, bands, band_name):
    """Join one reference-role column's wrapped lines (HDFC's RTGS UTR, Union's
    Sender No:, both split across two lines by the column's width). A pure
    'T' type-flag line contributes nothing (JPCB prints it on every row and
    it carries no information); everything else glues only at a genuine
    column-width clip, per `_ref_clip_wrap`, so two distinct codes stacked on
    adjacent lines (SBI's IMPS id + MOAD id) stay space-separated."""
    box = bands.get(band_name)
    if not box:
        return join_cell([cells_of(ln, bands).get(band_name) or "" for ln in block])
    lo, hi = box
    use_geom = _ref_has_from(block, bands)
    out, prev_clip = "", False
    for ln in block:
        words = []
        for w in sorted(ln.words, key=lambda w: w.x0):
            geom = _geom_role(w, bands)
            if use_geom:
                if geom != band_name or not _keep_ref_cell_word(w):
                    continue
            elif _word_role(w, bands, ln) != band_name:
                continue
            words.append(w)
        if not words:
            continue
        text = " ".join(w.text for w in words)
        if band_name == "reference" and text.strip().upper() == "T":
            continue
        clipped = words[-1].x1 >= hi - 10
        if not out:
            out = text
        elif out.endswith("-") or out.endswith("/"):
            out += text
        elif prev_clip and _ref_clip_wrap(out, text):
            out += text
        else:
            out += " " + text
        prev_clip = clipped
    return out.strip()


_REF_CELL_KEEP = {"TRANSFER", "FROM", "NO", "NO:", "UTR"}


def _keep_ref_cell_word(w):
    """Labels + account/UTR in a stacked TRANSFER/FROM cell; drop the
    duplicate company name that SBI reprints in the same column."""
    raw = (w.text or "").strip()
    up = raw.upper()
    if up in _REF_CELL_KEEP:
        return True
    return looks_like_instrument(raw)


def tidy_narration(s):
    """A clipped wrap often leaves a dangling '-', ':', '/' or ','."""
    t = (s or "").strip()
    cleaned = t.rstrip(" -:/,")
    return cleaned or t


def strip_echoed_reference(row):
    """HDFC reprints the joined UTR at the end of Particulars."""
    n = (row.get("narration") or "").strip()
    r = (row.get("reference") or "").strip()
    if len(r) >= 10 and n.endswith(r):
        row["narration"] = n[:-len(r)].rstrip(" -")
    return row


TRAILING_HASH_UTR = re.compile(
    r"^(.*?)\s+#\s+([A-Z]{4,}[A-Z0-9]{6,})(?:\s+(\d{3,8}))?\s*$", re.I)
TRAILING_UTR = re.compile(
    r"^(.*?)\s+([A-Z]{4,}\d{8,})\s*$", re.I)


def peel_trailing_ref(row):
    """JPCB prints UTR + instrument number in the description, with an empty
    INSNO/TYPE column after the type-flag T is dropped. Move them to Reference
    without taking loan-account wraps ('For : 021564…', 'For021800…')."""
    n = (row.get("narration") or "").strip()
    if (row.get("reference") or "").strip() or not n:
        return row
    m = TRAILING_HASH_UTR.match(n)
    if m:
        row["narration"] = m.group(1).strip()
        row["reference"] = " ".join(x for x in (m.group(2), m.group(3)) if x)
        return row
    m = TRAILING_UTR.match(n)
    if m:
        head = m.group(1).rstrip()
        if head.endswith(":") or head.lower().endswith("for"):
            return row
        row["narration"] = head
        row["reference"] = m.group(2)
    return row


_INLINE_VALUE_DATE_RX = re.compile(
    r"\s*\(Value\s+Date\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})\)", re.I)


def peel_value_date_from_narration(row):
    """Kotak embeds '(Value Date:21/06/2019)' in the narration when the value
    date column carries a different (often wrong) date. Use it as value_date;
    the annotation stays in narration because the PDF prints it there."""
    n = (row.get("narration") or "").strip()
    m = _INLINE_VALUE_DATE_RX.search(n)
    if not m:
        return row
    d = parse_date(m.group(1))
    if d:
        # rows_to_txns re-parses day-first, so an ISO string would swap to 2021-06-19
        row["value_date"] = d.strftime("%d/%m/%Y")
    return row


def polish_row(row):
    peel_chq_to_reference(row)
    peel_trailing_ref(row)
    peel_value_date_from_narration(row)
    strip_echoed_reference(row)
    n = row.get("narration")
    if n:
        row["narration"] = tidy_narration(n)
    return row


CHQ_LINE_RX = re.compile(r"^Chq:\s*\d+", re.I)
TXN_HEAD_RX = re.compile(
    r"^(UPI|IMPS|NEFT|RTGS|NACH|ECS|ACH)(/|\s)", re.I)
STOLEN_AFTER_CHQ_RX = re.compile(
    r"^(.*\bChq:\s*\d+)\s+(?=(?:UPI|IMPS|NEFT|RTGS)/)(.+)$", re.I | re.S)


def _line_narration(ln, bands):
    return (cells_of(ln, bands).get("narration") or ln.text() or "").strip()


def rehome_chq_tail(rows):
    """Canara e-passbook: 'Chq: 4168… UPI/CR/4534…' stole the next txn's start."""
    for i in range(len(rows) - 1):
        n = rows[i].get("narration") or ""
        m = STOLEN_AFTER_CHQ_RX.match(n.strip())
        if not m:
            continue
        head, tail = m.group(1).strip(), m.group(2).strip()
        rows[i]["narration"] = head
        nxt = rows[i + 1].get("narration") or ""
        if tail and tail not in nxt:
            rows[i + 1]["narration"] = f"{tail} {nxt}".strip() if nxt else tail
    return rows


INT_PD_RX = re.compile(r"^(.*?)(?:\s+|^)(\S+:\s*Int\.Pd:\s*\S+\s+to)\s*$", re.I)


def rehome_interest_rows(rows):
    """Quarterly savings-interest lines (e.g. Bank of Baroda):
    Row i has narration ending in '<acct>:Int.Pd:<from_date> to'.
    Row i+1 has the interest credit and balance, but blank narration.
    Row i+2 has no balance and holds the end date '<to_date>' in txn_date.
    Rehome the interest preamble to Row i+1 along with the end date.
    """
    for i in range(len(rows) - 2):
        n = rows[i].get("narration") or ""
        m = INT_PD_RX.match(n.strip())
        if not m:
            continue
        head, prefix = m.group(1).strip(), m.group(2).strip()
        rows[i]["narration"] = head
        end_date = rows[i + 2].get("txn_date") or ""
        if end_date:
            rows[i + 1]["narration"] = f"{prefix} {end_date}".strip()
        else:
            rows[i + 1]["narration"] = prefix
    return rows



def _cut_after_cheque(head, cut, bands):
    """Uniform line pitch ties the largest-gap split; Chq: is the real boundary.

    Canara prints wrap-above amounts, then time + 'Chq: <id>' below, then the
    next UPI/CR line. Equal 11.3pt gaps make the tie prefer the later index,
    gluing the next txn's narration onto this one.
    """
    limit = min(cut, len(head))
    for i in range(limit):
        if not CHQ_LINE_RX.match(_line_narration(head[i], bands)):
            continue
        j = i + 1
        if j < len(head) and TXN_HEAD_RX.match(_line_narration(head[j], bands)):
            return j
        break
    return cut


UTR_WRAP_RX = re.compile(
    r"^(?:[A-Z]{4,}[A-Z0-9]{6,}|[A-Z]{1,8}\d{6,}|\d{6,})(?:\s+\d{3,})?$", re.I)


def _keep_forward_wraps(head, cut, bands):
    """JPCB prints UTR / account wraps *below* the amounts. Uniform pitch
    assigns those ID-only lines to the next row; pull them back. This also
    covers a bare loan/account-number wrap ('02156400000020', 'For02180020000001')
    that has no letter-heavy UTR prefix -- still a pure-code line, still a
    tail of the row above rather than the row below."""
    while cut < len(head):
        t = re.sub(r"\s+", " ", _line_narration(head[cut], bands)).strip()
        if UTR_WRAP_RX.match(t):
            cut += 1
            continue
        break
    return cut


CHQ_TAIL_RX = re.compile(r"^(.*)\s+Chq:\s*(\S+)\s*$", re.I)


def peel_chq_to_reference(row):
    """Canara prints 'Chq: 416745…' as a narration line; there is no Ref header."""
    n = row.get("narration") or ""
    m = CHQ_TAIL_RX.match(n.strip())
    if not m:
        return row
    row["narration"] = m.group(1).strip()
    if not (row.get("reference") or "").strip():
        row["reference"] = m.group(2).strip()
    return row


# ---------- strategy 1: vertical-gap blocks ----------
def blocks_by_gap(lines, bands, k=1.6):
    if len(lines) < 3:
        return [[l] for l in lines]
    gaps = [lines[i + 1].top - lines[i].top for i in range(len(lines) - 1)]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return [[l] for l in lines]
    base = statistics.median(gaps)
    blocks, cur = [], [lines[0]]
    for i in range(1, len(lines)):
        if lines[i].top - lines[i - 1].top > base * k:
            blocks.append(cur); cur = [lines[i]]
        else:
            cur.append(lines[i])
    blocks.append(cur)
    return blocks


# ---------- strategy 2: balance-anchored ----------
def blocks_by_balance(lines, bands):
    """Every printed row carries exactly one running balance, so balance-bearing
    lines are 1:1 with transactions. Wrapped fragments are assigned to whichever
    anchor they sit closer to vertically, which handles both forward wrap (HDFC:
    narration spills below its own amounts) and backward wrap (JPCB/Canara:
    narration starts above them). A fragment that carries its own txn date always
    opens a new row, so it and everything after it belongs to the anchor below."""
    anchors, pending, out = [], [], []
    for ln in lines:
        if _has_balance(cells_of(ln, bands)):
            anchors.append((ln, pending)); pending = []
        else:
            pending.append(ln)
    tail = pending
    blocks = [[a] for a, _ in anchors]
    for k, (anchor, frags) in enumerate(anchors):
        prev = anchors[k - 1][0] if k > 0 else None
        forced = None
        for i, f in enumerate(frags):
            # a *complete* date opens a new row; a bare '2023' only continues one
            if is_date(cells_of(f, bands).get("txn_date", "")):
                forced = i; break
        head = frags[:forced] if forced is not None else frags
        rest = frags[forced:] if forced is not None else []
        if head:
            if prev is None:
                cut = 0
            else:
                # Split the run [prev, *head, anchor] at its largest vertical gap:
                # intra-cell line leading is tighter than the row pitch.
                # Gaps are rounded so that a table with uniform line pitch --
                # HDFC prints every line exactly 16.18pt apart -- ties instead of
                # being decided by float noise. A tie resolves to the largest
                # index, i.e. the fragment stays with the row above it, which is
                # the common forward-wrap case.
                seq = [prev] + head + [anchor]
                cut = max((round(seq[i + 1].top - seq[i].bottom, 1), i)
                          for i in range(len(seq) - 1))[1]
                # A fragment completing the previous row's split date
                # ('01-DEC-' + '2023') belongs to it regardless of spacing.
                while cut < len(head):
                    cur = join_cell([cells_of(l, bands).get("txn_date", "")
                                     for l in blocks[k - 1] + head[:cut]])
                    nxt = cells_of(head[cut], bands).get("txn_date", "")
                    if not cur or parse_date(cur) or not nxt:
                        break
                    if parse_date(join_cell([cur, nxt])):
                        cut += 1
                    else:
                        break
                cut = _cut_after_cheque(head, cut, bands)
                cut = _keep_forward_wraps(head, cut, bands)
                blocks[k - 1].extend(head[:cut])
            blocks[k].extend(head[cut:])
        blocks[k].extend(rest)
    if tail and blocks:
        # Wrapped narration after the last balance is real; page chrome is not.
        # Stop at the first footer/separator line so disclaimers cannot glue on.
        from .clean import is_chrome_line
        keep = []
        for ln in tail:
            if is_chrome_line(ln.text()):
                break
            keep.append(ln)
        blocks[-1].extend(keep)
    for b in blocks:
        b.sort(key=lambda l: (l.page, l.top))
    return [b for b in blocks if b]


# ---------- strategy 3: date-anchored (fallback for no-balance layouts) ----------
def blocks_by_date(lines, bands):
    blocks, cur = [], None
    for ln in lines:
        c = cells_of(ln, bands)
        if is_date(c.get("txn_date", "")):
            if cur: blocks.append(cur)
            cur = [ln]
        elif cur is not None:
            cur.append(ln)
    if cur: blocks.append(cur)
    return blocks


def resolve_date_cell(parts):
    """A wrapped narration can leak a token into the date band, which would poison
    a naive join. Prefer a part that is already a date, then the shortest run of
    consecutive parts that forms one ('01-DEC-' + '2023')."""
    for p in parts:
        if parse_date(p):
            return p
    for span in range(2, min(len(parts), 4) + 1):
        for i in range(len(parts) - span + 1):
            cand = join_cell(parts[i:i + span])
            if parse_date(cand):
                return cand
    return join_cell(parts)


def block_to_row(block, bands):
    """Merge a block's lines into one logical row, per column."""
    per = {k: [] for k in bands}
    for ln in block:
        c = cells_of(ln, bands)
        for k, v in c.items():
            if v:
                per[k].append(v)
    row = {}
    extras = []
    for k, parts in per.items():
        if k == "narration":
            row[k] = join_narration(block, bands)
        elif k in ("txn_date", "value_date"):
            resolved = resolve_date_cell(parts)
            extra = date_extra(resolved)
            row[k] = resolved
            if extra:
                extras.append(extra)
        elif k in ("debit", "credit", "balance", "amount"):
            # keep the single parseable amount; extra tokens are stray ink
            good = [p for p in parts if parse_amount(p)[0] is not None]
            row[k] = good[-1] if k == "balance" and good else (good[0] if good else join_cell(parts))
        elif _is_ref_role(k):
            row[k] = join_ref_band(block, bands, k)
        else:
            row[k] = join_cell(parts)
    refs = []
    for k in list(row):
        if not _is_ref_role(k):
            continue
        v = row.get(k) or ""
        if k != "reference":
            row.pop(k, None)
        if v.strip() and v.strip() not in {"-", "Sender"}:
            refs.append(v)
    if refs:
        row["reference"] = join_cell(refs)
    if extras:
        prefix = " ".join(extras)
        narr = row.get("narration") or ""
        if prefix and prefix not in narr:
            row["narration"] = f"{prefix} {narr}".strip()
    strip_echoed_reference(row)
    n = row.get("narration")
    if n:
        row["narration"] = tidy_narration(n)
    row["_page"] = block[0].page
    row["_top"] = block[0].top
    row["_nlines"] = len(block)
    row["_raw_lines"] = [ln.text() for ln in block]
    return row


def is_noise_row(row):
    d = parse_amount(row.get("debit") or "")[0]
    c = parse_amount(row.get("credit") or "")[0]
    b = parse_amount(row.get("balance") or "")[0]
    dt = parse_date(row.get("txn_date") or "")
    if dt and b is not None and (d is not None or c is not None):
        return False
    n = " ".join(x for x in (
        row.get("txn_date"), row.get("narration"), row.get("reference"),
        row.get("debit"), row.get("credit"), row.get("amount"),
    ) if x)
    return bool(NOISE_RX.search(n.strip()))
