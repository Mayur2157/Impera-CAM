"""Rule definitions, regex patterns, and normalization helpers for Indian bank narrations."""
from __future__ import annotations

import re

# --------------------------------------------------------------------------
# Channel Detection
# --------------------------------------------------------------------------
CHANNEL_PATTERNS = [
    ("UPI", re.compile(r"\b(?:UPI|VPA|BHIM|GPAY|PHONEPE|PAYTM)\b|@(?:ok|ybl|axl|paytm|apl|ibl|icici|hdfc|sbi)", re.I)),
    ("NEFT", re.compile(r"\bNEFT\b", re.I)),
    ("RTGS", re.compile(r"\bRTGS\b", re.I)),
    ("IMPS", re.compile(r"\bIMPS\b", re.I)),
    ("CASH", re.compile(r"\b(?:ATM|CASH|CWDR|CDM|EAW|NFS)\b", re.I)),
    ("CHEQUE", re.compile(r"\b(?:CHQ|CHEQUE|CLG|CTS|MICR|CLEARING)\b", re.I)),
    ("POS/CARD", re.compile(r"\b(?:POS|ECOM|DEBIT CARD|VISA|RUPAY|MASTERCARD|SWIPE|MERCHANT)\b", re.I)),
    ("MANDATE/ACH", re.compile(r"\b(?:NACH|ACH|ECS|STANDING INSTRUCTION|\bSI\b|AUTO\s*DEBIT)\b", re.I)),
    ("INTEREST", re.compile(r"\b(?:INT(?:\.|\s*PD|EREST)?|CREDIT INTEREST)\b", re.I)),
    ("CHARGES", re.compile(r"\b(?:CHG|CHARGE|FEE|PENAL|SMS|CONSOLIDATED|GST|IGST|CGST|SGST)\b", re.I)),
]

def detect_channel(narration: str) -> str:
    n = narration or ""
    for ch_name, rx in CHANNEL_PATTERNS:
        if rx.search(n):
            return ch_name
    return "TRANSFER/OTHER"

# --------------------------------------------------------------------------
# Category & Intent Patterns
# --------------------------------------------------------------------------

# Salary / Payroll
SALARY_RX = re.compile(
    r"\b(?:SALARY|SAL|PAYROLL|CMS/SAL|WAGES|STIPEND|MONTHLY SALARY|SAL CR)\b", re.I
)

# Loan & EMI Detection
EMI_RX = re.compile(
    r"\b(?:EMI|LOAN|BAJAJ\s*FIN|HDB\s*FS|MUTHOOT|CHOLAMANDALAM|CHOLA|SHRIRAM\s*CITY|"
    r"TATA\s*CAP|MAHINDRA\s*FIN|KREDITBEE|MONEYVIEW|DHANI|HOME\s*LOAN|CAR\s*LOAN|"
    r"AUTO\s*LOAN|PERS(?:ONAL)?\s*LOAN|L&T\s*FIN|ADITYA\s*BIRLA\s*FIN|HERO\s*FINCORP|"
    r"PIRAMAL|KOTAK\s*MAHINDRA\s*PRIME|POONAWALLA|FULLERTON|CLIX\s*CAPITAL|"
    r"IIFL|CAPITAL\s*FIRST|IDFC\s*FIRST\s*BHARAT|FINANCE\s*PVT|CREDIT\s*REPAYMENT)\b",
    re.I
)

# Loan Disbursals (Credits)
LOAN_DISBURSAL_RX = re.compile(
    r"\b(?:LOAN\s*DISB\w*|DISBURS\w*|LOAN\s*CREDIT|LOAN\s*PROCEEDS|LOAN\s*SANCTION|"
    r"KREDITBEE|MONEYTAP|CASHE|EARLYSALARY|FIBE|ZYPE)\b",
    re.I
)

# Utilities & Bills
UTILITY_RX = re.compile(
    r"\b(?:ELECTRICITY|BESCOM|MSEB|MSEDCL|TNEB|UPPCL|DHBVN|UHBVN|WBSEDCL|PSPCL|"
    r"TATA\s*POWER|ADANI\s*ELEC|TORRENT\s*POWER|WATER\s*BILL|GAS\s*BILL|IGL|MGL|MAHANAGAR\s*GAS|"
    r"INDANE|BHARAT\s*GAS|HP\s*GAS|AIRTEL(?!\s*PAYMENTS?\s*BANK)|JIO|VODAFONE|VI\b|BSNL|ACT\s*FIBERNET|HATHWAY|"
    r"BILLDESK|BBPS|PAYTM\s*BILL|PHONEPE\s*BILL)\b|RECHARGE",
    re.I
)

# Rent & Housing
RENT_RX = re.compile(r"\b(?:RENT|HOUSE\s*RENT|OFFICE\s*RENT|MAINTENANCE\s*CHG|HOUSING\s*SOCIETY)\b", re.I)

# Insurance
INSURANCE_RX = re.compile(
    r"\b(?:LIC|LIFE\s*INSURANCE|HDFC\s*LIFE|ICICI\s*PRU|SBI\s*LIFE|MAX\s*LIFE|BAJAJ\s*ALLIANZ|"
    r"TATA\s*AIA|KOTAK\s*LIFE|STAR\s*HEALTH|CARE\s*HEALTH|NIVA\s*BUPA|NEW\s*INDIA\s*ASSURANCE|"
    r"NATIONAL\s*INSURANCE|ORIENTAL\s*INSURANCE|UNITED\s*INDIA\s*INSURANCE|INSURANCE\s*PREM)\b",
    re.I
)

# Tax & Statutory
TAX_RX = re.compile(
    # statutory payees: tax, and the provident-fund / state-insurance contributions an employer remits
    r"\b(?:GST\b|INCOME\s*TAX|TDS|ADVANCE\s*TAX|CHALLAN|CBIC|CBDT|PROFESSIONAL\s*TAX|PTAX|"
    r"EPFO|ESIC|PROVIDENT\s*FUND|PF\s*CONTRIBUTION)\b", re.I
)

# Bounces & Rejections
BOUNCE_RX = re.compile(
    r"\b(?:BOUNCE|RETURN|RET|INSUFFICIENT\s*FUNDS?|DISHONOU?R|REJECT|ECS\s*RET|ACH\s*RET|"
    r"CHQ\s*RET|UNPAID|FAILED|REFER\s*TO\s*DRAWER)\b",
    re.I
)

# Bank Penalties & Service Charges
PENALTY_RX = re.compile(
    r"\b(?:MIN(?:IMUM)?\s*BAL\w*|NON\s*MAINT\w*|PENAL\w*|BOUNCE\s*CHG|RETURN\s*CHG|LATE\s*PAYMENT|"
    r"DEFAULT\s*CHG|CHEQUE\s*RETURN\s*CHG|OVERDUE)\b",
    re.I
)

# Self / Contra Transfers
SELF_TRANSFER_RX = re.compile(
    r"\b(?:SELF|OWN\s*A/?C|TRANSFER\s*TO\s*SELF|INTERNAL\s*TRANSFER|CONTRA|SWEEP|"
    r"TRF\s*(?:TO|FR)?\s*\d+|TRANSFER\s*(?:TO|FR)?\s*\d+|YOURSELF\s*FOR\s*DD|SELF\s*TRF|"
    r"TRF\s*NEW\s*RD|RD\s*A/?C)\b", re.I
)


# --------------------------------------------------------------------------
# Lender dictionary. A boost, not a gate: debt.py also finds unknown lenders
# by mandate channel and by repayment rhythm. Aliases cover renames
# (Fullerton → SMFG) and the truncated codes banks print (TPCF, TPCapfrst).
# --------------------------------------------------------------------------
LENDERS = [
    ("Bajaj Finance", r"BAJAJ\s*FIN|\bTPCF\b"),
    ("IDFC First Bank", r"IDFC\s*FIRST|TP\s*CAP\s*FRST|CAPITAL\s*FIRST"),
    ("SMFG India Credit (Fullerton)", r"FUL+ERTON|\bSMFG"),
    ("Hero FinCorp", r"HERO\s*FIN\s*CORP"),
    ("Shriram Finance", r"SHRIRAM\s*(?:CITY|TRANSPORT|FIN)"),
    ("Religare Finvest", r"RELIGARE"),
    ("Edelweiss", r"EDELWEISS"),
    ("SBFC Finance", r"\bSBFC\b"),
    ("HDB Financial Services", r"\bHDB\s*F"),
    ("Muthoot Finance", r"MUTHOOT"),
    ("Cholamandalam", r"\bCHOLA"),
    ("Tata Capital", r"TATA\s*CAP"),
    ("Mahindra Finance", r"MAHINDRA\s*(?:&\s*MAHINDRA\s*)?FIN"),
    ("L&T Finance", r"L\s*&\s*T\s*FIN|\bLTFS\b"),
    ("Aditya Birla Finance", r"ADITYA\s*BIRLA\s*FIN|\bABFL\b"),
    ("Piramal Finance", r"PIRAMAL"),
    ("Poonawalla Fincorp", r"POONAWALLA"),
    ("Clix Capital", r"\bCLIX"),
    ("IIFL Finance", r"\bIIFL\b"),
    ("KreditBee", r"KREDITBEE"),
    ("MoneyView", r"MONEY\s*VIEW"),
    ("Dhani Loans", r"\bDHANI\s*LOAN"),
    ("Kotak Mahindra Prime", r"KOTAK\s*(?:MAHINDRA\s*)?PRIME"),
    ("Lendingkart", r"LENDINGKART"),
    ("NeoGrowth", r"NEOGROWTH"),
    ("Capri Global", r"CAPRI\s*GLOBAL"),
    ("Ugro Capital", r"\bUGRO\b"),
    ("Fibe (EarlySalary)", r"\bFIBE\b|EARLYSALARY"),
    ("Navi Finserv", r"\bNAVI\s*FIN"),
]
_LENDER_RX = [(name, re.compile(pat, re.I)) for name, pat in LENDERS]

# A bank named as the payee of a mandate is a lender ('ECS/4009033/HDFC BANK LIMITED');
# the same bank named in a UPI VPA is not.
BANK_LENDER_RX = re.compile(
    r"\b(HDFC|ICICI|AXIS|KOTAK|SBI|STATE\s*BANK|YES|INDUSIND|IDBI|RBL|BANDHAN|FEDERAL)\s*BANK", re.I)

MANDATE_RX = re.compile(r"^(?:ACH|NACH|ECS)|\bNACH\b|\bECS\b|\bACH\b|ACHDR|ACH\s*DEBIT", re.I)

# Loan account named in the narration: 'LOAN INSTL PAYMENT-008633510000019',
# 'Loan Recovery For040770553605', 'Loan Account Payments For : 02156400000020'
LOAN_ACCOUNT_RX = re.compile(
    r"LOAN\s*(?:INSTL|INSTAL+MENT|RECOVERY|ACCOUNT\s*PAYMENTS?|REPAYMENT)?\s*(?:PAYMENTS?)?\s*"
    r"(?:FOR)?\s*[:\-]?\s*(\d{8,20})", re.I)
LOAN_CLOSED_RX = re.compile(r"PAY\s*OFF|FORECLOS|PRE\s*-?CLOS|LOAN\s*(?:A/?C\w*\s*)?CLOS", re.I)


def match_lender(text: str) -> str | None:
    """Canonical lender named anywhere in the narration, or None."""
    for name, rx in _LENDER_RX:
        if rx.search(text or ""):
            return name
    return None


# --------------------------------------------------------------------------
# Counterparty extraction: one grammar per channel, not per bank
# --------------------------------------------------------------------------
UNKNOWN = "Unknown"
IFSC_RX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")

# Channel words, labels and remarks that are never a party's name
_NOT_NAME_WORDS = {
    "NEFT", "RTGS", "IMPS", "UPI", "NEFTIN", "NEFTOUT", "RTGSIN", "RTGSOUT", "NEFTO", "RTGSO",
    "CR", "DR", "BY", "TO", "FROM", "TRANSFER", "TRF", "INB", "UTR", "NO", "FOR", "IN", "OUT", "O",
    "P2A", "P2M", "MB", "IB", "FT", "DEP", "CLG", "INST", "MICR", "CTS", "CHQ", "CHEQUE", "PAID",
    "RECEIVED", "MONEY", "SENT", "PAYMENT", "PAYMENTS", "ETXN", "TPT", "INTERNAL", "REF", "SENDER",
    "WDL", "DEPOSIT", "CUST", "ACCOUNT", "RETURN", "DOES", "NOT", "EXIST", "MUM", "BWY", "NA",
    "OW", "IW", "CMS", "BIL", "BILLPAY", "AP", "AT", "OD", "A/C", "AC", "ACH", "ACHDR", "DEBIT",
    "CREDIT", "NACH", "ECS", "CLEARING", "FUNDS", "TR", "WDL", "PRCR", "MOB", "REV", "PURCHASE", "POS",
}
_CASH_RX = re.compile(r"^(?:BY\s+CASH|CASH\b|CASH\s*DEP|CWDR|ATM\b|NFS\b|TO\s+CASH|TO\s+SELF\b|SELF\b)", re.I)
_BANK_POSTED_RX = re.compile(
    # whole words only: 'RECHARGE' (a mobile top-up) is not a 'CHARGE'
    r"INT\.?\s*(?:COLL|PD)|\bINTEREST\b|\bCHARGES?\b|\bCHGS?\b|\bCHRG\b|\bSGST\b|\bCGST\b|\bIGST\b|"
    r"\bREJECTED\b|CLOSURE\s*PROCEEDS|PAY\s*OFF|STOP\s*PAY|\bCIBIL\b|\bCERSAI\b|\bSBINT\b|"
    r"\bOD\s*INT\b|^(?:IW|OW|I/W|O/W)\b|RT-CHG|HRETCHARGE|LIEN\s*MARKING", re.I)
# 'GST PAYMENT', and 'RTGS :GST :RESERVE BANK OF INDIA' (the tax as its own field)
_TAX_PAYEE_RX = re.compile(
    r"^\s*(?:GST|TDS|INCOME\s*TAX|CBDT|CBIC)\b|[:/\-]\s*(?:GST|TDS|CBDT|CBIC)\s*[:/\-]", re.I)
_ACCOUNT_NO_RX = re.compile(r"(?<![A-Z0-9])(\d{9,18})(?![0-9])")


# HDFC-style customer payment: '<account>-<remark>' or '<account>-TPT-<remark>'
# '<account>-<remark>': the account may carry letters ('3017FA2000158574-STP-DIESEL')
_ACCT_TOKEN = r"(?=[0-9A-Z]*(?:\d[^\d\s-]*){9})\d[0-9A-Z]{8,17}"
CUSTOMER_REMARK_RX = re.compile(rf"^\s*{_ACCT_TOKEN}\s*-", re.I)


def _strip_ids(s: str) -> str:
    """Drop UTRs, RRNs and account numbers, including ones glued to a name:
    'KCCBN19148059321BHAIRAV' → 'BHAIRAV', 'KHYATI INTERNATI0112966287' →
    'KHYATI INTERNATI', 'HI TECH MOULDSR069203…' → 'HI TECH MOULDS'."""
    s = re.sub(r"\b[A-Z]{2,6}\d{6,}(?=[A-Z]{3,})", " ", s)
    s = re.sub(r"\b[A-Za-z]{0,6}\d{5,}\w*", " ", s)
    s = re.sub(r"(?<=[A-Za-z])[A-Z]?\d{6,}\w*", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _name_part(field: str) -> str | None:
    """A field's name, or None when it is only ids, channel words or an IFSC."""
    f = (field or "").strip().upper()
    if not f or IFSC_RX.match(f.replace(" ", "")):
        return None
    f = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", f)
    # a name printed before a transaction id ends at the id: what follows is
    # the bank's code or a remark ('K P ENTERPRISES BCBMH19224764352 SRCB').
    # Only when the text before the id is itself a name ('CR. FOR NEFT <id>
    # K.P.ENTERPRISE' has only channel words before it)
    m = re.match(r"^(.*?[A-Z]{2,}.*?)\s+[A-Z]{0,6}\d{8,}\w*(?:\s|$)", f)
    if m and not re.match(r"\s*\d", m.group(1)):
        before = _name_core(m.group(1))
        if before:
            return before
    return _name_core(f)


def _name_core(f: str) -> str | None:
    f = _strip_ids(f)
    words = [w for w in re.split(r"[\s.:,~]+", f) if w]
    while words and words[0].rstrip(":.") in _NOT_NAME_WORDS:
        words.pop(0)
    # a rail word after the name starts the remitting bank's details
    # ('OASYS NEFT STATE BANK OF INDIA' → 'OASYS')
    for k, w in enumerate(words[1:], start=1):
        if w in ("NEFT", "RTGS", "IMPS", "UPI"):
            words = words[:k]
            break
    while words and words[-1].rstrip(":.") in _NOT_NAME_WORDS:
        words.pop()
    # SBI prints both lines of a two-line cell interleaved: 'GLOBAL GLOBAL CONNECTION CONNECTION'
    words = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]
    # a flat / plot number ('F.14 PANT NAGA', 'B 02 …') is an address, not a name
    if len(words) >= 2 and len(words[0]) <= 2 and words[0].isalpha() and words[1].isdigit():
        return None
    name = " ".join(words)
    if sum(c.isalpha() for c in name) < 4:
        return None
    return name


def _vpa_label(text: str) -> str | None:
    m = re.search(r"([A-Za-z0-9._\-]{3,})@", text or "")
    if not m:
        return None
    local = m.group(1).strip("._-")
    return f"VPA {local}" if local else None


def extract_counterparty(narration: str, reference: str = "", own_accounts=()) -> str:
    """Party on the other side of the transaction, or 'Unknown'.

    Never returns a channel label ('NEFTIn', 'By Transfer'), an IFSC code or a
    UTR. An account number is used only when no name is printed, labelled
    'A/c <number>' so it is not mistaken for a name."""
    n = (narration or "").strip()
    if not n:
        return UNKNOWN
    # '_' separates fields like a space or '/' ('0386_CERSAI CHARGES_191726809')
    u = n.upper().replace("_", " ")

    u = re.sub(r"\bM/S\.?\s*", "", u)
    # '<account>-<remark>' is a payment the customer made; its remark
    # ('HIRING CHARGES') is theirs, not a fee the bank posted
    customer_initiated = bool(CUSTOMER_REMARK_RX.match(u))
    if _BANK_POSTED_RX.search(u) and not customer_initiated:
        return "Bank"
    if _CASH_RX.search(u) or re.search(r"CASH\s+DEP|CASH\s+DEPOSIT", u):
        return "Cash"
    if _TAX_PAYEE_RX.search(u):
        return "Tax Authority"
    if MANDATE_RX.search(u):
        lender = match_lender(u)
        if lender:
            return lender
    if re.match(r"^CR\s+CUST\s+ACCOUNT", u):
        return UNKNOWN          # JPCB prints the payer only in its annexure table

    m = LOAN_ACCOUNT_RX.search(u)
    if m:
        return match_lender(u) or f"Loan A/c {m.group(1)}"

    # ---- UPI ----
    if re.match(r"^UPI\b", u):
        # Canara / Bandhan: UPI/<DR|CR>/<rrn>/<NAME>/<bank>/<vpa>/…
        m = re.match(r"^UPI[/-](?:DR|CR|REV)/[A-Z]?\d+/([^/]+)/", u)
        if m and _name_part(m.group(1)) and not re.search(r"\d", m.group(1)):
            return _clean_name(_name_part(m.group(1)))
        vpa = _vpa_label(n)
        if vpa:
            return vpa
        # no handle printed: a field that is a name of two or more words
        # ('UPI/<ref>/<acct>/<IFSC>/MR H MOHAMMED HAKKEEM/LIC PREMI')
        for field in u.split("/")[1:]:
            name = _name_part(field)
            if name and len(name.split()) >= 2 and not re.search(r"\d", field):
                return _clean_name(name)
        # Cosmos clips the handle before the '@': 'UPI-DR/<rrn>/bharatpe098939'
        last = n.rstrip("/").rsplit("/", 1)[-1].strip()
        # …but a bare payment hash ('HDF8F7B0B8DF6EE4…', Bandhan) is not a handle
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9._\-]{3,19}", last) and sum(c.isalpha() for c in last) >= 3 \
                and last.upper() not in _NOT_NAME_WORDS:
            return f"VPA {last}"
        return UNKNOWN

    # ---- IMPS ----
    if "IMPS" in u:
        m = re.search(r"IMPS\s+FROM\s+(.+?)\s+REF\b", u)                    # Kotak
        if m and _name_part(m.group(1)):
            return _clean_name(_name_part(m.group(1)))
        # SBI masks the other account ('XXXX644KVBL' out, 'XX0644' in): keep the
        # last three digits so both directions name the same account
        m = re.search(r"(?<![A-Z])X{2,}\s*X*(\d{3,4})(?:[A-Z]{4})?\b", u)
        if m:
            return f"A/c XXXX{m.group(1)[-3:]}"
        m = re.search(r"IMPS/P2[AM]/\d+/([^/]+)", u)                         # BoB
        if m:
            name = _name_part(m.group(1))
            if name:
                return _clean_name(name)
            # 'IMPS/P2A/<ref>/7045652906/9': the payer is named only by mobile
            mob = m.group(1).strip()
            return f"Mobile {mob}" if re.fullmatch(r"[6-9]\d{9}", mob) else UNKNOWN

    # ---- Kotak mobile banking: the text after MB: is the payee ----
    m = re.match(r"^MB:\s*(?:RECEIVED\s+MONEY\s+FROM\s+|SENT\s+TO\s+)?(.+)$", u)
    if m and _name_part(m.group(1)):
        return _clean_name(_name_part(m.group(1)))

    # ---- HDFC '<account>-<remark>': the payee is not printed ----
    m = re.match(rf"^({_ACCT_TOKEN})\s*-\s*[A-Z]", u)
    if m:
        acct = m.group(1)
        return UNKNOWN if acct in set(own_accounts) else f"A/c {acct}"

    # ---- Cheques: 'BY CLG INST 9976:SBI AT AHMEDABAD' names the drawee bank ----
    if re.search(r"\bCLG\s+INST\s+\d+\s*:", u):
        return UNKNOWN

    # ---- Transfers printed as '<from> TO <to>': the party is the beneficiary ----
    # ('CHEQUE WDL- FUNDS TR GLOBAL CONNECTION TO TANCOM ELECTRONICS')
    m = re.search(r"\b(?:FUNDS\s+TR|TRANSFER|TRF)\b\s+.+?\s+TO\s+([A-Z][A-Z .&']+?)(?:-\d+)?\s*$", u)
    if m and _name_part(m.group(1)):
        return _clean_name(_name_part(m.group(1)))

    # ---- '… FRM / FROM <name>': the name after it is the remitter ----
    # ('FUND TRF/ 618 / FRM THE PEACE MISSION PRIVATE LIMI')
    m = re.search(r"\b(?:FRM|FROM)\s+([A-Z][A-Z0-9 .&']{3,})$", u)
    if m and _name_part(m.group(1)):
        return _clean_name(_name_part(m.group(1)))

    # ---- Everything else (NEFT/RTGS/transfers/cheques/plain names) ----
    fields = [f for f in re.split(r"[/*|#]|-|:(?=\s*[A-Z])", u) if f.strip()]
    for f in fields:
        name = _name_part(f)
        if name:
            return _clean_name(name)

    # A number after NEFT/RTGS/IMPS is a transaction id, not an account
    m = None if re.match(r"^(?:NEFT|RTGS|IMPS)\b", u) else _ACCOUNT_NO_RX.search(u)
    if m and m.group(1) not in set(own_accounts):
        return f"A/c {m.group(1)}"
    return UNKNOWN


_NAME_STOPWORDS = {"M/S", "MS", "M", "S", "PVT", "PRIVATE", "LTD", "LT", "LIMITED", "LLP", "CO", "AND",
                   "THE", "P", "L", "INC", "COMPANY", "OF", "&"}


def norm_name(s: str) -> str:
    """Comparable form of a party name: 'M/S. Heena Cargo Movers P Ltd' → 'HEENA CARGO MOVERS'."""
    t = (s or "").upper().replace("&", " AND ")
    t = re.sub(r"^(?:M/S|MR|MRS|MS|SMT|VPA|A/C)\b\.?", " ", t)
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    return " ".join(w for w in t.split() if w not in _NAME_STOPWORDS)


def same_party(a: str, b: str) -> bool:
    """Names of one party printed differently: truncated ('TANMAY INTERNATI'),
    reordered ('SHAIKH SOHEB') or with suffixes ('P LTD' / 'PRIVATE LIMITED')."""
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # spaces dropped by the bank: 'FABFACTHEAVYENGINEERINGPVTLTD'
    ca, cb = sorted((na.replace(" ", ""), nb.replace(" ", "")), key=len)
    if len(ca) >= 10 and cb.startswith(ca):
        return True
    short, long_ = sorted((na, nb), key=len)
    # truncated name, or the holder named inside a longer one
    # ('SANMAN DIVISION OF IMPERATIVE BUSINESS' vs 'IMPERATIVE BUSINESS VENTURES')
    if len(short) >= 10 and (long_.startswith(short) or f" {short}" in f" {long_}"):
        return True
    lcp = 0
    for i in range(len(long_)):
        if i == 0 or long_[i - 1] == " ":
            k = 0
            while k < len(short) and i + k < len(long_) and long_[i + k] == short[k]:
                k += 1
            lcp = max(lcp, k)
    if lcp >= 10 and lcp >= 0.6 * len(short):
        return True
    # every word a prefix of the other name's words, in order ('SOHEB USM' / 'SOHEB USMAN SHAIKH')
    ws, wl = short.split(), long_.split()
    if len(ws) >= 2 and ws[0] == wl[0] and len(ws) <= len(wl) and \
            all(wl[i].startswith(w) and len(w) >= 3 for i, w in enumerate(ws)):
        return True
    ta, tb = set(na.split()), set(nb.split())
    return len(ta & tb) / len(ta | tb) >= 0.9


def _clean_name(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9\s&.,'-]", " ", raw or "")
    s = re.sub(r"\s+", " ", s).strip(" .-_:,")
    if s.isupper():
        s = s.title()
    return s or UNKNOWN


def _drops_letters(longer: str, shorter: str) -> bool:
    """`shorter` is `longer` with one or two letters left out (a doubled or
    missed letter: FLUTTINGS / FLUTINGS, SALUNKHE / SALUNKE)."""
    if not 1 <= len(longer) - len(shorter) <= 2 or len(shorter) < 5:
        return False
    it = iter(longer)
    return all(ch in it for ch in shorter)


def same_name_variant(a: str, b: str) -> bool:
    """Spelling variants of one name, not two different names.

    Merged: a letter or two dropped in one word, or one name a truncation of
    the other. Not merged: a substituted letter (RAJESH / RAMESH, SHIN /
    SHIV are different people) or different numbers (two loan accounts,
    TDS sections 92B and 94C)."""
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb or na == nb:
        return bool(na) and na == nb
    if re.findall(r"\d+", na) != re.findall(r"\d+", nb):
        return False
    short, long_ = sorted((na, nb), key=len)
    if len(short) >= 12 and long_.startswith(short):
        return True
    ta, tb = na.split(), nb.split()
    if len(ta) != len(tb):
        return False
    diff = [(x, y) for x, y in zip(ta, tb) if x != y]
    return len(diff) == 1 and _drops_letters(*sorted(diff[0], key=len, reverse=True))
