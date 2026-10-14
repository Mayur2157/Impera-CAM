"""Account / customer header extraction. Regex over the pre-table text of page 1."""
import re
from collections import defaultdict
from .normalize import parse_date

FIELDS = [
    ("account_number", r"(?:CASA\s*)?(?:A\s*/?\s*c\.?|Account)\s*(?:No\.?|Number)?\s*[:\-]\s*"
                       r"([0-9Xx\*]{6,25})\b"),
    ("account_number", r"(?:A\s*/?\s*c\.?|Account)\s*(?:No\.?|Number)\s*[:\-]*\s+([0-9Xx\*]{6,25})\b"),
    ("account_number", r"(?:Savings|Current|CC|OD|SB)\s+Account\s*[\-:]?\s*([0-9Xx\*]{9,25})\b"),
    ("account_number", r"Statement\s+for\s+A\s*/?\s*c\s+([0-9Xx\*]{6,25})\b"),
    ("customer_name",  r"(?:Account\s*(?:Holder\s*)?(?:Name|Title)|Name\s*of\s*the\s*Customer|"
                       r"Customer\s*Name|Account\s*Title)\s*[:\-]?\s*([A-Z][A-Za-z0-9&.,'\-/]+(?:\s[A-Za-z0-9&.,'\-/]+)*)"),
    ("customer_id",    r"(?:Customer\s*(?:Id|No|ID|Number)|Cust\.?\s*(?:ID|Reln\.?\s*No\.?)|CIF\s*(?:ID|No\.?)?)"
                       r"(?:\s*[:\-]+\s*|\s+)(?=[A-Za-z\*\-]*\d)([A-Za-z0-9Xx\*\-]{3,25})"),
    ("customer_number", r"Customer\s*Number\s*[:\-]?\s*(\d{6,15})"),
    ("ifsc",           r"\b(?:RTGS\s*/?\s*NEFT\s*)?IFS?C?\s*(?:Code)?\s*[:\-]*\s*([A-Z]{4}0[A-Z0-9]{6})\b"),
    ("ifsc_alt",       r"\b([A-Z]{4}0[A-Z0-9]{6})\b"),
    ("micr",           r"MICR\s*(?:Code)?\s*[:\-]*\s*(\d[\d ]{7,12}\d)"),
    ("account_type",   r"(?:Account\s*(?:Type|Description)|Product\s*(?:Name|Type)|Type|Scheme)\s*"
                       r"[:\-]+\s*([A-Za-z][A-Za-z0-9_\-/]+(?:\s[A-Za-z0-9_\-/]+)*)"),
    # Union prints 'Account Type Current Account' with no colon
    ("account_type",   r"Account\s*Type[ \t]+([A-Za-z][A-Za-z ]+?)(?:[ \t]{2,}|$)"),
    # BoB: 'Statement of transactions in Savings Account 52880100009033'
    ("account_type",   r"transactions\s+in\s+((?:Savings|Current|Cash\s*Credit|Overdraft)\s+Account)"),
    # a labelled product code ('Product Code : CA-GEN'); numeric codes mean
    # nothing without the bank's own table, so only the prefix is ever used
    ("product_code",   r"Product\s*Code\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-]{1,20})"),
    # A printed limit; 0.00 (HDFC 'OD Limit', SBI 'Drawing Power') means none
    ("od_limit",       r"(?:OD\s*Limit|Drawing\s*Power|Sanction(?:ed)?\s*Limit|Limit\s*Amount|DP\s*Limit)"
                       r"\s*[:\-]?\s*([\d,]+\.\d{2})"),
    ("joint_holder",   r"Joint\s*Holders?\s*[:\-]+\s*/?\s*([A-Z][A-Za-z .&/]{3,80}?)\s*(?:\s{2,}|$)"),
    ("email",         r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"),
    ("phone",          r"(?:Mob(?:ile)?\.?\s*No\.?|Phone(?:\s*no\.?)?|Contact\s*no\.?)\s*[:\-]?\s*"
                       r"(\+?\d[\d\- ]{7,15})"),
    ("pan",            r"\bPAN\s*(?:NO\.?)?\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z]|[X]{5,}\d{3,}[A-Z])"),
    ("currency",       r"Currency(?:\s*Name)?\s*[:\-]?\s*([A-Za-z ]{3,20})"),
]
PERIOD = [
    r"(?:for\s*the\s*period\s*(?:of)?|Statement\s*Period\s*(?:From)?|period\s*of)\s*[:\-]?\s*"
    r"([\d]{1,2}[\-/][\w]{2,9}[\-/][\d]{2,4}|\w{3}\s*\d{1,2},?\s*\d{4})\s*(?:to|To|-|–)\s*"
    r"([\d]{1,2}[\-/][\w]{2,9}[\-/][\d]{2,4}|\w{3}\s*\d{1,2},?\s*\d{4})",
    r"From\s*(?:Date)?\s*[:\-]?\s*([\d]{1,2}[\-/][\w]{2,9}[\-/][\d]{2,4})\s*"
    r"To\s*(?:Date)?\s*[:\-]?\s*([\d]{1,2}[\-/][\w]{2,9}[\-/][\d]{2,4})",
    # SBI: "Account Statement from 1 Sep 2020 to 21 Nov 2020"
    r"Account\s+Statement\s+from\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\s+to\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})",
]

IFSC_MAP = {
    "HDFC": "HDFC Bank", "SBIN": "State Bank of India", "ICIC": "ICICI Bank",
    "UTIB": "Axis Bank", "KKBK": "Kotak Mahindra Bank", "PUNB": "Punjab National Bank",
    "BARB": "Bank of Baroda", "CNRB": "Canara Bank", "UBIN": "Union Bank of India",
    "IOBA": "Indian Overseas Bank", "IDIB": "Indian Bank", "CBIN": "Central Bank of India",
    "MAHB": "Bank of Maharashtra", "BKID": "Bank of India", "UCBA": "UCO Bank",
    "IDFB": "IDFC First Bank", "YESB": "Yes Bank", "INDB": "IndusInd Bank",
    "FDRL": "Federal Bank", "KVBL": "Karur Vysya Bank", "RATN": "RBL Bank",
    "SRCB": "Saraswat Co-operative Bank", "COSB": "The Cosmos Co-operative Bank",
    "BCBM": "Bharat Co-operative Bank (Mumbai)", "DNSB": "Dombivli Nagari Sahakari Bank",
    "JPCB": "The Jalgaon Peoples Co-op Bank", "BDBL": "Bandhan Bank",
    "NKGS": "NKGSB Co-operative Bank", "SVCB": "SVC Co-operative Bank",
    "ABHY": "Abhyudaya Co-operative Bank", "TJSB": "TJSB Sahakari Bank",
    "PMCB": "Punjab & Maharashtra Co-op Bank", "KJSB": "Kalyan Janata Sahakari Bank",
    "AUBL": "AU Small Finance Bank", "DBSS": "DBS Bank India", "SIBL": "South Indian Bank",
    "CIUB": "City Union Bank", "KARB": "Karnataka Bank", "DCBL": "DCB Bank",
    "JAKA": "J&K Bank", "PSIB": "Punjab & Sind Bank", "IBKL": "IDBI Bank",
    "UTBI": "United Bank of India", "ALLA": "Allahabad Bank", "ORBC": "Oriental Bank",
    "CORP": "Corporation Bank", "ANDB": "Andhra Bank", "SYNB": "Syndicate Bank",
    "VIJB": "Vijaya Bank", "DEUT": "Deutsche Bank", "CITI": "Citibank",
    "SCBL": "Standard Chartered", "HSBC": "HSBC India", "HVBK": "Shinhan Bank",
}

BANKS = [("HDFC Bank", r"HDFC\s*BANK"), ("State Bank of India", r"\bSBI\b|STATE BANK OF INDIA"),
         ("Kotak Mahindra Bank", r"KOTAK"), ("Bank of Baroda", r"BANK\s*OF\s*BARODA"),
         ("Canara Bank", r"CANARA\s*BANK"), ("Union Bank of India", r"UNION\s*BANK"),
         ("United Bank of India", r"UNITED\s*BANK\s*OF\s*INDIA"),
         ("Bandhan Bank", r"BANDHAN"), ("The Cosmos Co-operative Bank", r"COSMOS\s*CO"),
         ("Bharat Co-op Bank", r"BHARAT\s*CO"), ("Dombivli Nagari Sahakari Bank", r"DOMBIVLI\s*NAGARI|DNS\s*BANK"),
         ("The Jalgaon Peoples Co-op Bank", r"JALGAON\s*PEOPLES"), ("ICICI Bank", r"ICICI\s*BANK"),
         ("Axis Bank", r"AXIS\s*BANK"), ("Punjab National Bank", r"PUNJAB\s*NATIONAL"),
         ("IDFC First Bank", r"IDFC\s*FIRST"), ("Yes Bank", r"\bYES\s*BANK\b")]

# Short names that only a file name uses ('cosmos Bank.pdf')
_FILENAME_BANKS = [("The Cosmos Co-operative Bank", r"\bCOSMOS\b")]

# Email patterns that belong to the branch/bank, not the customer
_BRANCH_EMAIL_HINTS = re.compile(
    r"@(?:jpcbank|bandhanbank|canarabank|bankofindia|sbi|pnb|axisbank|kotakbank|"
    r"hdfcbank|icicibank|unionbankofindia|syndicatebank|cbi|iob|bob|"
    r"obc|vijayabank|andhrbank|andhrabank|vijaya)\.", re.I)


HEAD_X_TOL = 1.5
_CID_RX = re.compile(r"\(cid:\d+\)")

# 'MR. LAKSHMAN KUMAR', 'M/S. HEENA CARGO …' → the name without the title
_HONORIFIC_RX = re.compile(r"^(?:M/S|MRS|MR|MS|SMT)(?:\.+\s*|\s+)", re.I)

# Lines in the customer block that are the bank's, not the customer's
_BANK_LINE_RX = re.compile(r"\bBANK\b|\bBRANCH\b|\bBR\.", re.I)


def _clean(v):
    v = re.sub(r"\s+", " ", v).strip(" :-,.")
    return v


def _words_to_line_groups(words, y_tol=None):
    """Group pdfplumber word dicts by y-position, return list of (top, [word, …]).

    Clusters by distance, not by rounding. The tolerance follows the page's
    own line spacing (0.4 of the typical gap between lines) rather than a
    fixed number of points: Union prints a value 3.7pt above its label
    ('919820215633' over 'Mobile No'), still well inside one 11pt line."""
    if y_tol is None:
        tops = sorted({round(w["top"], 1) for w in words})
        gaps = sorted(b - a for a, b in zip(tops, tops[1:]) if b - a > 1.0)
        # the upper quartile is the real line pitch; smaller gaps are the
        # value/label offsets themselves and would understate it
        y_tol = max(3.5, 0.4 * gaps[(3 * len(gaps)) // 4]) if gaps else 3.5
    groups = []
    for w in sorted(words, key=lambda w: w["top"]):
        if groups and w["top"] - groups[-1][0] <= y_tol:
            groups[-1][1].append(w)
        else:
            groups.append((w["top"], [w]))
    return [(top, sorted(ws, key=lambda w: w["x0"])) for top, ws in groups]


def _split_columns(words, page_width):
    """Split header words into left/right column text.

    Many two-column layouts (HDFC, Canara, Kotak, Union) print customer info
    on the left and branch/account info on the right. We find the horizontal
    whitespace corridor nearest to the page centre and use it as the boundary.
    """
    if not words:
        return "", ""
    mid = page_width / 2.0
    line_groups = _words_to_line_groups(words)
    # Leave centred titles out of the corridor search. 'Account Statement'
    # sits across the gap between the customer block and the label column and
    # would hide it, leaving only the label/value gap. A title is a line of a
    # single block (no internal gap) that crosses the middle of the page.
    def is_centred_title(ws):
        ws = sorted(ws, key=lambda w: w["x0"])
        one_block = not any(b["x0"] - a["x1"] >= 20 for a, b in zip(ws, ws[1:]))
        return one_block and ws[0]["x0"] < mid < ws[-1]["x1"]
    corridor_words = [w for _, ws in line_groups if not is_centred_title(ws) for w in ws] or words
    # Gather all x gaps inside the page to find the dominant internal corridor
    sorted_xs = sorted((w["x0"], w["x1"]) for w in corridor_words)
    # Build a simple gap list: pairs (gap_start, gap_end) between consecutive x1 and next x0
    xs_flat = []
    for x0, x1 in sorted_xs:
        xs_flat.append((x0, "s"))
        xs_flat.append((x1, "e"))
    xs_flat.sort()
    # Candidate corridor: the widest gap between 25% and 75% of page_width
    best_gap, best_pos = 0.0, mid
    open_count = 0
    last_e = None
    for x, t in xs_flat:
        if t == "s":
            if open_count == 0 and last_e is not None:
                gap = x - last_e
                if gap > best_gap and page_width * 0.25 <= last_e <= page_width * 0.75:
                    best_gap, best_pos = gap, (last_e + x) / 2.0
            open_count += 1
        else:
            open_count -= 1
            last_e = x
    boundary = best_pos if best_gap >= 20 else mid

    left_lines, right_lines = [], []
    for _, ws in line_groups:
        ws = sorted(ws, key=lambda w: w["x0"])
        cut = _line_cut(ws, boundary)
        l = " ".join(w["text"] for w in ws[:cut])
        r = " ".join(w["text"] for w in ws[cut:])
        if l.strip():
            left_lines.append(l)
        if r.strip():
            right_lines.append(r)
    return "\n".join(left_lines), "\n".join(right_lines)


def _line_cut(ws, boundary, min_gap=10.0, slack=15.0):
    """Index where one header line splits into its left and right blocks.

    Split only at a real whitespace gap near the boundary. A line printed
    straight across it (Jalgaon's 'MALLIKARJUN APPARTMENT,,MADHAV SANSAR,…')
    has no such gap and stays whole on the side where it starts."""
    for i in range(1, len(ws)):
        if (ws[i]["x0"] - ws[i - 1]["x1"] >= min_gap
                and ws[i]["x0"] >= boundary - slack
                and ws[i - 1]["x1"] <= boundary + slack):
            return i
    if ws and ws[0]["x0"] >= boundary - slack:
        return 0
    return len(ws)


def _extract_address(head_text: str) -> str | None:
    lines = head_text.splitlines()
    addr_lines = []
    in_addr = False
    addr_col = 0
    stop_rx = re.compile(
        r"^(STATEMENT\s*OF|Transactions\s*in|Period\b|From\s*Date|From\s*\d|To\s*Date|"
        r"Opening\s*Balance|SN\b|Date\b|TRANS\b|Tran\b|Customer\s*Number|Account\s*No|"
        r"Nominee|Branch\s*GSTIN|Date\s*:-|A/C\s*No|Product\s*Type|Branch\s*ID|IFSC|MICR|"
        r"Joint\s*Holder|Branch\s*Phone)",
        re.I,
    )
    for line in lines:
        if not line.strip():
            if in_addr and addr_lines:
                break
            continue
        parts = [p.strip() for p in re.split(r"\s{2,}", line) if p.strip()]
        if not parts:
            continue
        if not in_addr:
            for idx, part in enumerate(parts):
                m = re.match(r"^(?:Customer\s*|Account\s*)?Address\s*[:\-]?\s*(.*)$", part, re.I)
                if m and not re.search(r"^(?:Email|Branch|Web)\b", part, re.I):
                    in_addr = True
                    addr_col = idx
                    val = m.group(1).strip()
                    if not val and idx + 1 < len(parts):
                        nxt_p = parts[idx + 1]
                        if not re.search(r"^(?:Branch|Email|Station|Date|Phone)", nxt_p, re.I):
                            val = nxt_p
                    if val and not val.upper().startswith("AADHAR"):
                        addr_lines.append(val)
                    break
        else:
            first = parts[0]
            if stop_rx.search(first) or (re.search(r"^[A-Za-z\s]{3,20}[:\-]", first)
                                         and not re.search(r"^(?:Tal|Near|Plot|Flat|Shop|Room|Bldg|Road|Floor|Sector|Dist|AADHAR)", first, re.I)):
                break
            chosen = parts[addr_col] if len(parts) > addr_col else parts[0]
            if stop_rx.search(chosen) or (re.search(r"^[A-Za-z\s]{3,20}[:\-]", chosen)
                                          and not re.search(r"^(?:Tal|Near|Plot|Flat|Shop|Room|Bldg|Road|Floor|Sector|Dist|AADHAR)", chosen, re.I)):
                break
            chosen = re.sub(r"^(?:Date\s*[:\-]|Page\s*[:-]).*$", "", chosen, flags=re.I).strip()
            chosen = re.sub(r"^AADHAR\s*[:\-]*\s*", "", chosen, flags=re.I).strip()
            if chosen and chosen not in addr_lines:   # SBI reprints the first line
                addr_lines.append(chosen)
            if len(addr_lines) >= 8:
                break
    if addr_lines:
        res = _clean(" ".join(addr_lines))
        res = re.sub(r"\s*Date\s*[:\-].*$", "", res, flags=re.I).strip(" ,;:-")
        if len(res) >= 5:
            return res[:160]
    m = re.search(r"(?<!Email\s)(?<!Branch\s)\bAddress\s*[:\-]?\s*(.{5,160})", head_text, re.I | re.S)
    if m:
        first_segment = [x.strip() for x in re.split(r"\s{2,}|\n", m.group(1)) if x.strip()]
        if first_segment:
            return _clean(first_segment[0])[:160]
    return None


_ADDR_STOP_RX = re.compile(
    r"\bStatement\b|^(?:JOINT\s*HOLDER|Nomination|Nominee|From\b|Statement|Period|Records|Date\b|"
    r"Mobile|E-?mail|Phone|Tel\b|Contact|Sl\.?\s*No|Txn|Tran|Account|A/C|Customer|CIF|"
    # the bank's own details follow the customer block (ebrcpt 'BRANCH ADDRESS:')
    r"Branch|IFSC|MICR|RTGS|NEFT|Swift)|"
    # any 'Label:' line ends the customer's address: an address line is not a label
    r"^[A-Za-z][A-Za-z ./]{1,25}:", re.I)
# Union labels each address part: 'City MUMBAI', 'State Maharashtra', 'Zip 400066'
_ADDR_PART_LABEL_RX = re.compile(r"^(?:City|State|Country|Zip|Pin(?:\s*Code)?)\s*[:\-]?\s+", re.I)


def _address_under_name(left_head, name):
    """Unlabelled customer block: name, then address lines (HDFC, Kotak, Union)."""
    if not left_head or not name:
        return None
    lines = [ln.strip() for ln in left_head.splitlines()]
    start = next((i for i, ln in enumerate(lines) if name in ln), None)
    if start is None:
        return None
    parts = []
    for ln in lines[start + 1:]:
        if not ln:
            continue
        if _ADDR_STOP_RX.search(ln):
            break
        ln = _ADDR_PART_LABEL_RX.sub("", ln).strip()
        if re.fullmatch(r"[\W_]*", ln):
            continue          # Kotak prints a lone '.' for an empty line
        parts.append(ln)
        if len(parts) >= 8:
            break
    res = _clean(" ".join(parts))
    return res[:160] if len(res) >= 5 else None


def _search_all(pat, *texts, flags=re.I | re.M):
    """Try a pattern against multiple text sources, return first match group(1)."""
    for t in texts:
        if not t:
            continue
        m = re.search(pat, t, flags)
        if m:
            return _clean(m.group(1))
    return None


def extract_customer(pdf, header_top=None, source_name=None):
    """Only the region above the transaction table is parsed. Narration text is
    full of IFSC codes and bank names; reading it would poison every field.

    Two-column layout aware: customer info is on the left side; bank/branch
    info is on the right. We parse the left column preferentially for fields
    like customer name, address, email and phone, and the right column for
    bank/branch metadata. This prevents HDFC and Canara address mixing.
    """
    p0 = pdf.pages[0]
    if header_top and header_top > 30:
        region = p0.crop((0, 0, p0.width, min(header_top, p0.height)))
    else:
        region = p0
    # HDFC sets header words ~1.9pt apart; the default 3pt tolerance welds
    # 'HEENA CARGO MOVERS' into one token.
    head = (region.extract_text(layout=True, x_tolerance=HEAD_X_TOL)
            or region.extract_text(x_tolerance=HEAD_X_TOL) or "")
    head = _CID_RX.sub(" ", head)
    # Two-column split via word bounding boxes
    try:
        words = []
        for w in region.extract_words(x_tolerance=HEAD_X_TOL):
            t = _CID_RX.sub("", w["text"]).strip()
            if t:
                words.append({**w, "text": t})
        left_head, right_head = _split_columns(words, p0.width)
    except Exception:
        left_head, right_head = head, ""
    info = {}
    # Run FIELDS against the full header first, then left/right individually
    for key, pat in FIELDS:
        if info.get(key):
            continue
        if key == "ifsc_alt":
            if info.get("ifsc"):
                continue
            key = "ifsc"
        m = re.search(pat, head, re.I | re.M)
        if m and not info.get(key):
            info[key] = _clean(m.group(1))

    # ------------------------------------------------------------------ #
    # Customer e-mail: prefer non-branch email from the left column.      #
    # Jalgaon prints branch email on the right, customer email on left.   #
    # ------------------------------------------------------------------ #
    # The holder's mobile, from the customer's side of the header only, and
    # only a real 10-digit mobile number. Branch landlines ('Phone no. :
    # 022-61606161', 'PHONE NO.: 25349005') stay as printed in 'phone' but are
    # never used to identify the holder.
    info["mobile"] = None
    for m in re.finditer(r"(?:Mob(?:ile)?\.?\s*(?:No\.?)?|Phone(?:\s*no\.?)?|Contact\s*no\.?)\s*[:\-]?\s*(\+?[\d][\d\- ]{8,15}\d)",
                         left_head or "", re.I):
        digits = re.sub(r"\D", "", m.group(1))[-10:]
        if len(digits) == 10 and digits[0] in "6789":
            info["mobile"] = digits
            break
    if not info.get("phone") and info.get("mobile"):
        info["phone"] = info["mobile"]

    info.pop("email", None)
    for line in head.splitlines():
        for m in re.finditer(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", line):
            label = line[max(0, m.start() - 25):m.start()]
            if _BRANCH_EMAIL_HINTS.search(m.group(1)) or re.search(r"\b(?:BR|Branch)\.?\s*E-?mail", label, re.I):
                continue
            info["email"] = _clean(m.group(1))
            break
        if info.get("email"):
            break

    # ------------------------------------------------------------------ #
    # Customer name: try labelled patterns first, then unlabelled.        #
    # ------------------------------------------------------------------ #
    if info.get("customer_name"):
        # Multi-line continuation (United Bank: 'JASMINE ELECTRONICS AND' + 'ELECTRICALS')
        name = info["customer_name"]
        lines = head.splitlines()
        for idx, ln in enumerate(lines):
            if name in ln and idx + 1 < len(lines):
                nxt = lines[idx + 1].strip()
                parts = [p.strip() for p in re.split(r"\s{2,}", nxt) if p.strip()]
                if parts:
                    cand = parts[0]
                    if (re.search(r"\b(?:AND|&|,|\-)\s*$", name, re.I) or (cand.isupper() and len(cand) > 2)) \
                            and not re.search(r"[:\-]|(?:Address|Date|Branch|IFSC|MICR|Account|Phone|Email|Statement)\b", cand, re.I):
                        info["customer_name"] = f"{name} {cand}".strip()
                break
    else:
        # 0. Bare 'Name' label at the start of a left-column line (Canara);
        #    'Branch Name' sits mid-line or in the right column.
        m_nm = re.search(r"^\s*Name\s*[:\-]?\s+([A-Z][A-Za-z0-9&.,'\-/ ]{2,80})$", left_head, re.M)
        if m_nm:
            info["customer_name"] = _clean(m_nm.group(1))
    if not info.get("customer_name"):
        # 1. 'To :' / 'TO' block (Jalgaon). The left column keeps the right-hand
        #    'IFSC Code' off the 'TO :' line so the name is on the next line.
        m_to = None
        for src in (left_head, head):
            m_to = re.search(
                r"^\s*To\s*[:\-]?\s*\n\s*([A-Z][A-Za-z0-9&.,'\-/ ]{2,80})",
                src, re.I | re.M)
            if m_to:
                break
        if m_to:
            cand = _clean(m_to.group(1))
            # Exclude lines that are address lines or contain only symbols
            if not re.search(r"[:]|(?:Address|Date|Branch|IFSC|MICR|Account|Phone|Email|Statement)\b", cand, re.I):
                info["customer_name"] = cand
        if not info.get("customer_name"):
            # 2. Unlabelled before NOMINATION REGISTERED (Bharat Co-op)
            m_co = re.search(r"\n\s*([A-Z][A-Z0-9\s.,&\'-]{2,50})\s{2,}NOMINATION\s+REGISTERED", head)
            if m_co:
                info["customer_name"] = _clean(m_co.group(1))
        if not info.get("customer_name"):
            # 3. Left column: first substantial ALL-CAPS line that is not a bank/address label
            #    (Kotak: TANMAY INTERNATIONAL; Union: VIDHI SALES CORPORATION)
            _SKIP = re.compile(
                r"^(?:Account|Statement|Period|Page|Date|From|To|Branch|IFSC|MICR|"
                r"Phone|Email|Fax|Tel|Web|Customer\s*Id|Customer\s*No|Product|Currency|"
                r"Nomination|Joint|Record|Balance|Opening|Drawing|Interest|CIF|GSTIN|PAN|"
                r"A/C\s*No|MR\.|MRS\.|DR\.)\b",
                re.I)
            for ln in left_head.splitlines():
                ln = ln.strip()
                if not ln or len(ln) < 4:
                    continue
                # Must look like a name: mostly alpha, no colons, not a label
                # ('M/S. HEENA CARGO …' is one; the bank's own title line is not)
                # …and no dates or account numbers: 'DDA 20190716 42710540422' is a code
                if (re.fullmatch(r"[A-Z][A-Z0-9\s&.,\'/()-]{3,80}", ln) and not _SKIP.search(ln)
                        and not _BANK_LINE_RX.search(ln) and not re.search(r"\d{4,}", ln)):
                    info["customer_name"] = _clean(ln)
                    break
        if not info.get("customer_name"):
            # 4. 'MR./MRS./M/S' prefix (BoB: 'MR. LAKSHMAN KUMAR')
            m_mr = re.search(
                r"\b(?:MR\.?|MRS\.?|MS\.?|M/S\.?|SHRI|SHREE)\s+([A-Z][A-Za-z0-9&.\s\'-]{2,60})",
                head, re.I)
            if m_mr:
                info["customer_name"] = _clean(m_mr.group(1))
    if info.get("customer_name"):
        info["customer_name"] = _HONORIFIC_RX.sub("", info["customer_name"]).strip() \
            or info["customer_name"]

    # ------------------------------------------------------------------ #
    # Branch detection                                                     #
    # ------------------------------------------------------------------ #
    # Prefer right-column 'Branch Name' label (Canara)
    m_br_name = re.search(
        r"Branch\s*Name\s*(?:[:\-]+\s*|\s+)([A-Za-z][A-Za-z0-9,.\-/& ]{1,40})", right_head or head, re.I)
    if m_br_name:
        cand = _clean(m_br_name.group(1))
        if not re.search(r"^(?:Phone|ID|GSTIN|Address)\b", cand, re.I):
            info["branch"] = cand
    if not info.get("branch"):
        m_br = re.search(
            r"(?:Branch\s*(?:of\s*Ownership|Name|Code)?|Account\s*Branch)\s*(?:[:\-]+|\bCode\b)\s*"
            r"([A-Za-z0-9,.\-/&]+(?:\s[A-Za-z0-9,.\-/&]+)*)",
            head, re.I)
        if m_br and not re.search(r"^(?:Phone|ID|GSTIN|Address)\b", m_br.group(1), re.I):
            cand = _clean(m_br.group(1))
            # Skip pure numeric branch codes (Canara '2579') — already handled above
            if not re.fullmatch(r"\d{2,8}", cand):
                info["branch"] = cand
    if not info.get("branch"):
        m_tr = re.search(r"Account\s*No\s*[:\-]*\s*\d+\s+([A-Za-z0-9,.\-/& ]+?\s+Branch)\b", head, re.I)
        if m_tr:
            info["branch"] = _clean(m_tr.group(1))
    # Right-column plain 'Branch   S V RD, BORIVALI' (Union)
    if not info.get("branch"):
        m_rbr = re.search(
            r"(?:Branch)\s+([A-Za-z][A-Za-z0-9,.\-/& ]{2,40})", right_head, re.I)
        if m_rbr:
            cand = _clean(m_rbr.group(1))
            if not re.fullmatch(r"\d{2,8}", cand):
                info["branch"] = cand

    # ------------------------------------------------------------------ #
    # Period                                                              #
    # ------------------------------------------------------------------ #
    for pat in PERIOD:
        m = re.search(pat, head, re.I)
        if m:
            info["period_from"] = parse_date(_clean(m.group(1))) or _clean(m.group(1))
            info["period_to"] = parse_date(_clean(m.group(2))) or _clean(m.group(2))
            break

    # ------------------------------------------------------------------ #
    # Bank identity                                                       #
    # ------------------------------------------------------------------ #
    if info.get("ifsc"):
        info["bank"] = IFSC_MAP.get(info["ifsc"][:4].upper()) or info.get("bank")
    if not info.get("bank"):
        up = head.upper()
        for name, pat in BANKS:
            if re.search(pat, up):
                info["bank"] = name; break
    if not info.get("bank"):
        # only lines outside the transaction table: a wrapped narration line
        # ('…:HDFC BANK LIMITED', a payee's bank) is not the statement's bank
        txnish = re.compile(r"\d{1,2}[\-/][\w]{2,9}[\-/]\d{2,4}|\d[\d,]*\.\d{2}")
        outside = []
        for pg in pdf.pages[:2]:
            lines = (pg.extract_text() or "").splitlines()
            rows = [i for i, ln in enumerate(lines) if txnish.search(ln)]
            if rows:
                lines = lines[:rows[0]] + lines[rows[-1] + 1:]
            outside += lines
        for line in outside:
            if txnish.search(line):
                continue
            if not re.search(r"(bank\s*(limited|ltd)|registered\s*office|co[\- ]?operative|"
                             r"multi\s*-?\s*state|customer\s*care|www\.|\\.in\b|\.com\b|"
                             r"proprietary\s*software|head\s*office|\bHO[: ])", line, re.I):
                continue
            for name, pat in BANKS:
                if re.search(pat, line, re.I):
                    info["bank"] = name; break
            if info.get("bank"):
                break

    # Kotak: bank name missing from header text (logo only) — infer from IFSC
    if not info.get("bank") and info.get("ifsc", "").upper().startswith("KKBK"):
        info["bank"] = "Kotak Mahindra Bank"
    # Last resort: the logo is an image (Kotak, Cosmos 'Imperative'), but the
    # uploaded file is usually named after the bank.
    if info.get("bank"):
        info["bank_source"] = "statement"
    if not info.get("bank") and source_name:
        name = _bank_from_file_name(source_name)
        if name:
            info["bank"], info["bank_source"] = name, "file name"

    # ------------------------------------------------------------------ #
    # Opening balance                                                     #
    # ------------------------------------------------------------------ #
    m = re.search(r"(?:Opening\s*Balance|Balance\s*as\s*on[^:]*)\s*[:\-]?\s*"
                  r"([\-\d,]+\.\d{2}\s*(?:Cr|Dr)?)", head, re.I)
    if m:
        info["opening_balance_printed"] = _clean(m.group(1))

    # ------------------------------------------------------------------ #
    # Address (left column preferred)                                     #
    # ------------------------------------------------------------------ #
    addr = _extract_address(left_head or head)
    if not addr:
        # HDFC's labelled 'Address :' is the branch's (right column); the
        # customer's address is the unlabelled block under their name.
        addr = _address_under_name(left_head, info.get("customer_name"))
    if not addr:
        addr = _extract_address(head)
    if addr:
        info["address"] = addr
    # date of the opening / balance-forward line ('16 Jun 19 16 Jun 19 BALANCE
    # FORWARD 114,453.65'): where the statement's balance coverage begins,
    # though it is not a transaction
    d = _opening_balance_date(pdf)
    if d:
        info["opening_balance_date"] = d
    return info


def _bank_from_file_name(source_name):
    r"""Bank named in the file name. Uploads arrive as 'cosmos_Bank.pdf' /
    'Union_bank.pdf': '_' is a word character and defeats the patterns' \b
    and \s*, so separators are read as spaces first."""
    fname = re.sub(r"[_\-.]+", " ", source_name or "")
    for name, pat in BANKS + _FILENAME_BANKS:
        if re.search(pat, fname, re.I):
            return name
    return None


_OPENING_LINE_RX = re.compile(
    r"^\s*(\d{1,2}[\s/\-.](?:\d{1,2}|[A-Za-z]{3,9})[\s/\-.,]+\d{2,4})\b.*?"
    r"\b(?:BALANCE\s*(?:B/?F|FORWARD|BROUGHT\s*FORWARD)|OPENING\s*BALANCE|B/F)\b", re.I)


def _opening_balance_date(pdf):
    """Date printed on the first page's opening / balance-forward line."""
    if not pdf.pages:
        return None
    for line in (pdf.pages[0].extract_text() or "").splitlines():
        m = _OPENING_LINE_RX.match(line)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d
    return None


