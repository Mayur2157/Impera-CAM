"""Indian bank statement value normalisation. Money is always Decimal."""
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

# 1,23,456.78 | 1,234,567.89 | 12345.67 | 1.234,56 is NOT expected in INR statements
AMOUNT_RX = re.compile(r"^[\(\-\+]?\s*(?:(?:Rs\.?|INR)\s*)?([0-9][0-9,]*(?:\.[0-9]{1,3})?)\s*"
                       r"(cr|dr|c|d)?\s*[\)]?$", re.I)
TRAILING_FLAG_RX = re.compile(r"(cr|dr)\s*$", re.I)

DATE_FORMATS = [
    "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
    "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b %y",
    "%d-%B-%Y", "%d %B %Y", "%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y",
]
# Search, not full-string match: BoB prints '08-06-2023 ACH' in the date column.
DATE_RX = re.compile(
    r"(\d{1,2}[\-/. ](?:\d{1,2}|[A-Za-z]{3,9})[\-/. ]\d{2,4})")


def _try_parse_date_token(raw):
    raw = re.sub(r"\s+", "-", raw.strip()).replace("/", "-").replace(".", "-")
    parts = raw.split("-")
    if len(parts) == 3 and parts[1].isalpha():
        parts[1] = parts[1][:3].title()
        raw = "-".join(parts)
    for fmt in ("%d-%m-%Y", "%d-%m-%y", "%d-%b-%Y", "%d-%b-%y", "%d-%B-%Y"):
        try:
            d = datetime.strptime(raw, fmt).date()
            if 1990 <= d.year <= 2100:
                return d
        except ValueError:
            continue
    return None


MONTH_FIRST_RX = re.compile(
    r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{2,4})\b")


def parse_date(s):
    """Parse a date, ignoring trailing column leftovers such as 'ACH'."""
    if not s:
        return None
    s = s.strip().rstrip(",")
    m_mf = MONTH_FIRST_RX.search(s)
    if m_mf:
        month, day, year = m_mf.group(1)[:3].title(), m_mf.group(2), m_mf.group(3)
        fmt = "%d-%b-%Y" if len(year) == 4 else "%d-%b-%y"
        try:
            d = datetime.strptime(f"{day}-{month}-{year}", fmt).date()
            if 1990 <= d.year <= 2100:
                return d
        except ValueError:
            pass
    m = DATE_RX.search(s)
    if not m:
        return None
    return _try_parse_date_token(m.group(1))


def date_extra(s):
    """Non-date tokens sharing the date cell ('08-06-2023 ACH' → 'ACH')."""
    if not s:
        return ""
    m = DATE_RX.search(s.strip())
    if not m:
        return ""
    extra = (s[:m.start()] + " " + s[m.end():]).strip(" -/,\t")
    return extra


def complete_partial_date(raw, year):
    """'05-DEC-' or '14 Oct' plus a year from a neighbouring row."""
    if not raw or not year:
        return None
    s = re.sub(r"[\s\-/.,]+$", "", str(raw).strip())
    if not s:
        return None
    return parse_date(f"{s}-{year}") or parse_date(f"{s} {year}")


YEAR_RX = re.compile(r"^(?:19|20)\d{2}$")
MONTH_RX = re.compile(
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*$", re.I)
DAY_RX = re.compile(r"^(0?[1-9]|[12]\d|3[01])$")


def looks_like_date_fragment(s):
    """True for a real date, a year wrap ('2023'), a day/month token, or
    '05-DEC-' / '14 Oct'.

    SBI prints '1 Sep 2020' as three words in the date band. BoB wraps
    '/Payme' into the same band — those must stay narration.
    """
    t = (s or "").strip().rstrip(".,")
    if not t:
        return False
    if parse_date(t):
        return True
    if YEAR_RX.match(t) or MONTH_RX.match(t) or DAY_RX.match(t):
        return True
    return complete_partial_date(t, 2000) is not None \
        or complete_partial_date(t, 2024) is not None


def is_date(s):
    return parse_date(s) is not None


def parse_amount(s):
    """Returns (Decimal, flag) where flag in {'CR','DR',None}. None value if not an amount."""
    if s is None:
        return None, None
    t = s.strip()
    if not t or t in {"-", "--", "."}:
        return None, None
    neg = t.startswith("(") and t.endswith(")")
    m = AMOUNT_RX.match(t)
    if not m:
        return None, None
    body, flag = m.group(1), m.group(2)
    body = body.replace(",", "")
    try:
        v = Decimal(body)
    except InvalidOperation:
        return None, None
    if neg or t.lstrip().startswith("-"):
        v = -v
    f = None
    if flag:
        f = "CR" if flag[0].lower() == "c" else "DR"
    return v, f


def looks_numeric(s):
    v, _ = parse_amount(s)
    return v is not None


def split_glued(cell):
    """'-1,00,99,262.60' or '5420125.81 DR' -> value + flag. Also splits a date
    glued to text by the extractor, e.g. 'SHRIVASTAV121050102442612/04/2021'."""
    return parse_amount(cell)
