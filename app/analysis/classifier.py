"""Layer 3: Transaction Classification Engine.

Categorizes every transaction into standardized banking categories,
tags counterparties, and identifies operating vs. financing vs. contra flows.

A row that matches no rule and has no identifiable party is UNCLASSIFIED,
never BUSINESS_RECEIPT / BUSINESS_EXPENSE: an unfamiliar bank format should
produce an honest "can't tell", not a confident wrong income figure.
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict
from typing import Any

from .narration_rules import (
    SALARY_RX,
    EMI_RX,
    LOAN_DISBURSAL_RX,
    UTILITY_RX,
    RENT_RX,
    INSURANCE_RX,
    TAX_RX,
    PENALTY_RX,
    SELF_TRANSFER_RX,
    MANDATE_RX,
    BANK_LENDER_RX,
    LOAN_ACCOUNT_RX,
    LOAN_CLOSED_RX,
    CUSTOMER_REMARK_RX,
    UNKNOWN,
    detect_channel,
    extract_counterparty,
    match_lender,
    norm_name,
    same_party,
)
from .returns import find_returns
from .entities import assign_entities

# Credit Card repayments
CREDIT_CARD_RX = re.compile(
    r"\b(?:CRED\b|CREDIT\s*CARD|CC\s*PAYMENT|SBI\s*CARD|SBICARD|HDFC\s*CARD|ICICI\s*CARD|KOTAKCARD|"
    r"AMEX|AMERICAN\s*EXPRESS|ONE\s*CARD|RBL\s*CARD|KOTAK\s*CARD|AXIS\s*CARD|CITI\s*CARD)\b",
    re.I,
)

# Investments (MF, Securities, FD, Gold)
INVESTMENT_RX = re.compile(
    r"\b(?:MUTUAL\s*FUND|ZERODHA|GROWW|UPSTOX|ANGEL\s*ONE|NIPPON|HDFC\s*AMC|ICICI\s*PRU\s*MF|"
    r"SBI\s*MF|KOTAK\s*MF|UTI\s*MF|NSE\b|BSE\b|SECURITIES|BROKERAGE|FIXED\s*DEPOSIT|\bFD\b|"
    r"TERM\s*DEPOSIT|SWEEP\s*IN|SWEEP\s*OUT|GOLD\s*SOVEREIGN|"
    r"APY|ATAL\s*PENSION|NPS|PRAN|PPF|SUKANYA)\b",
    re.I,
)

# Interest (Credits or Debits like OD interest)
INTEREST_RX = re.compile(
    r"\b(?:INT(?:\.|\s*PD)?|CREDIT\s*INTEREST|SAVINGS\s*INTEREST|INT\.COLL|INTEREST\s*DEBIT|SBINT|"
    r"OD\s*INTEREST|OD\s*INT|OVERDRAFT\s*INTEREST|LOAN\s*INTEREST|INTEREST\s*CAPITALI[SZ]ED)\b",
    re.I,
)

# Refunds & Reversals (credits). 'NEFT RETURN-ACCOUNT DOES NOT EXIST' gives back
# the customer's own failed payment; it is not income.
REFUND_RX = re.compile(
    r"\b(?:REFUND|REVERSAL|REV|REVD|CASHBACK|FAILED\s*TXN\s*REV|CHARGEBACK|REVERTED|"
    r"NEFT\s*RETURN|RTGS\s*RETURN|IMPS\s*RETURN|RETURNED|CREDIT\s*ADJUSTMENT|REWARDS?|"
    r"GOOGLEINDIADIGI|GOOG-PAYMENT|CLOSURE\s*PROCEEDS|CR\s*ADJ|DISCOUNT)\b",
    re.I,
)

# Cash transactions
CASH_RX = re.compile(
    r"\b(?:ATM|CASH|CWDR|CDM|EAW|NFS|BY\s*CASH|TO\s*CASH|CASH\s*DEP|CASH\s*WDL)\b|^(?:TO\s+)?SELF\b",
    re.I,
)

# Bank service charges: never a penalty on their own
SERVICE_CHARGE_RX = re.compile(
    r"\bCHGS?\b|\bCHARGES?\b|\bCHRG\b|\bFEE\b|\bCIBIL\b|\bCERSAI\b|INTERCHANGE|\bAMC\b|\bSMS\b|"
    r"(?:S|C|I)GST\s*\d+\s*PERCENT|\bGST\s*ON\b|MMSREGCHARGE|STOP\s*PAY", re.I)

# The customer's own remark that money is a loan to / from a person
_PERSONAL_LOAN_RX = re.compile(r"(?:^|[/\s\d])LOAN\b|\bUDHAR\b|\bHAND\s*LOAN\b", re.I)

# payment channels the customer initiates; their remarks are the customer's words
_CUSTOMER_CHANNEL_RX = re.compile(r"^(?:UPI|IMPS|NEFT|RTGS|MB|IB|ETXN|TPT|FT\b|TO\s+CLG|CHQ\s+PAID)", re.I)
# a remark with RENT glued to a short prefix ('/PGRENT /'); not CURRENT, PARENT, TORRENT, DIFFERENT
_GLUED_RENT_RX = re.compile(r"\b(?!CUR|PA|TOR|DIFFE|APPA)[A-Z]{1,6}RENT\b", re.I)
# money loaded into a wallet: spending moves out of sight, so it is labelled as such
_WALLET_RX = re.compile(r"ADD-?MONEY|WALLET\s*(?:LOAD|TOP)|\bTOP-?UP\b|LOAD\s*MONEY", re.I)
# Bharat Bill Payment System: a bill paid, biller not named in the narration
_BBPS_RX = re.compile(r"BBPS", re.I)

REVERSAL_DR_RX = re.compile(r"\bWRNG\b|\bWRONG\b.*\bREV|\bREVERSAL\b|\bREV\s+DT\b", re.I)

# Own deposits held at the same bank (recurring deposit, sweep)
OWN_DEPOSIT_RX = re.compile(r"\bTO\s+RD\b|TRF\s+TO\s+RD\b|\bRD\s*A/?C\b|TRF\s*NEW\s*RD", re.I)

_BUSINESS_NAME_RX = re.compile(
    r"\b(?:LTD|LIMITED|PVT|PRIVATE|LLP|ENTERPRISES?|TRADERS|TRADING|CORPORATION|CORP|INDUSTRIES|"
    r"INTERNATIONAL|AGENC(?:Y|IES)|SALES|SERVICES|SOLUTIONS|ELECTRONICS|ELECTRICALS|ENGINEERING|"
    r"MOVERS|VENTURES|CONNECTION|STORES|FIRM|ASSOCIATES|EXPORTS?|IMPORTS?|CO)\b", re.I)
# Leading words too common to tie two businesses together
_GENERIC_FIRST = {"SHREE", "SHRI", "SREE", "SRI", "GLOBAL", "INDIA", "INDIAN", "NEW", "STAR", "ROYAL",
                  "UNITED", "NATIONAL", "GENERAL", "SUPER", "MODERN", "CITY", "THE", "JAI", "OM"}
_NOT_A_PARTY = {UNKNOWN, "Bank", "Cash", "Tax Authority"}


def _is_party(cp: str) -> bool:
    return bool(cp) and cp not in _NOT_A_PARTY


class Holder:
    """Who the account belongs to: name, whether it is a business, own accounts."""

    def __init__(self, name: str = "", account_number: str = "", joint_holders=(), email: str = "",
                 phone: str = ""):
        self.name = (name or "").strip()
        # the holder's registered mobile: a UPI handle built on it is theirs
        # ('9146585866@ybl', or masked '**85866@YBL')
        digits = re.sub(r"\D", "", phone or "")
        self.phone = digits[-10:] if len(digits) >= 10 else ""
        self.loan_accounts: set[str] = set()
        self.linked: list[dict] = []        # other holders sharing contact details
        # the part before '@', lower-cased: 'vasaexport@gmail.com' → 'vasaexport'
        self.email_local = re.sub(r"[^a-z]", "", (email or "").split("@")[0].lower())
        # the person the holder lives care of: 'CO USMAN YASIN SHAIKH THAGARI …'
        self.care_of: list[str] = []
        self.joint_holders = [j for j in joint_holders if j]
        self.norm = norm_name(self.name)
        self.account = re.sub(r"\D", "", str(account_number or ""))
        self.is_business = bool(_BUSINESS_NAME_RX.search(self.name))
        self.own_accounts: set[str] = set()
        toks = self.norm.split()
        self.first_token = toks[0] if toks and len(toks[0]) >= 5 and toks[0] not in _GENERIC_FIRST else ""
        # an individual's other names (surname, father's name) mark family members
        self.family_tokens = {w for w in toks if len(w) >= 4} if not self.is_business else set()

    def owns_handle(self, narration: str) -> bool:
        if not self.phone:
            return False
        for m in re.finditer(r"(?:\*+)?(\d{5,12})@", narration or ""):
            digits, masked = m.group(1), m.group(0).startswith("*")
            if digits[-10:] == self.phone or (masked and self.phone.endswith(digits)):
                return True
        return False

    def is_self(self, cp: str, narration: str = "", party_account: str = "") -> bool:
        if party_account and party_account in self.own_accounts:
            return True
        if self.owns_handle(narration):
            return True
        if _is_party(cp) and any(same_party(cp, n) for n in [self.name, *self.joint_holders] if n):
            return True
        if any(re.search(rf"(?<!\d){a}(?!\d)", narration or "") for a in self.own_accounts):
            return True
        return False


def _own_accounts_in(narration: str, holder: Holder, reference: str = "") -> set[str]:
    """Account numbers in a narration. The number after 'NEFT :' / 'RTGS :' is
    the bank's transaction id, not an account (JPCB 'RTGS : 000002261956'),
    and so is a UPI reference ('UPI/REV/432062501645/SOHEB USM/…') or any
    number printed as the row's own reference."""
    n = narration or ""
    if LOAN_ACCOUNT_RX.search(n) or re.match(r"^\s*(?:NEFT|RTGS|IMPS)\s*[:\-]", n, re.I):
        return set()
    txn_ids = {(reference or "").strip().lstrip("0")}
    m = re.match(r"^\s*UPI[/\-](?:[A-Z]{2,3}[/\-])?[A-Z]?(\d+)", n, re.I)
    if m:
        txn_ids.add(m.group(1).lstrip("0"))
    return {a for a in re.findall(r"(?<!\d)(\d{9,18})(?!\d)", n)
            if a != holder.account and a.lstrip("0") not in txn_ids}


def classify_transaction(txn: dict, customer_name: str = "", holder: Holder | None = None) -> dict[str, Any]:
    """Classify a single transaction with Category, Subcategory, Counterparty, and Traits."""
    holder = holder or Holder(customer_name)
    # '_' separates fields like a space ('0386_CERSAI CHARGES_191726809'), so
    # word rules see them; the stored narration is not changed
    narr = (txn.get("narration") or "").strip().replace("_", " ")
    ref = (txn.get("reference") or "").strip()
    crd = float(txn["credit"]) if txn.get("credit") else 0.0
    deb = float(txn["debit"]) if txn.get("debit") else 0.0
    is_credit = crd > 0
    channel = detect_channel(narr)

    own = [holder.account] if holder.account else []
    cp = extract_counterparty(narr, ref, own)
    if txn.get("party_hint"):
        cp = extract_counterparty(txn["party_hint"]) if not _is_party(cp) or cp.startswith("A/c") else cp
    lender = match_lender(narr)

    # the bank's own postings (charges on an own-account RTGS) are never
    # transfers, unless they name an own account ('<RD a/c> : Closure Proceeds')
    names_own_account = any(a in narr for a in holder.own_accounts)
    is_self = (cp != "Bank" or names_own_account) and bool(
        holder.is_self(cp, narr, txn.get("party_account") or "")
        or OWN_DEPOSIT_RX.search(narr)
        or (SELF_TRANSFER_RX.search(narr) and not CASH_RX.search(narr))
    )

    def out(cat, subcat, *, rev=False, op=False, fin=False, contra=False):
        return {
            "category": cat, "subcategory": subcat, "counterparty": cp,
            "is_revenue": rev, "is_operating_expense": op,
            "is_financing": fin, "is_contra": contra,
        }

    # ----------------------------------------------------------------------
    # Credits
    # ----------------------------------------------------------------------
    if is_credit:
        if is_self:
            return out("SELF_TRANSFER_CR", "Own Account Transfer", contra=True)
        if REFUND_RX.search(narr) or re.match(r"^UPI[/-]REV", narr, re.I):
            return out("REFUND_REVERSAL", "Refund / Reversal / Cashback")
        if LOAN_DISBURSAL_RX.search(narr) or (
                lender and crd >= 50000 and channel != "UPI"):
            return out("LOAN_DISBURSEMENT", "Loan Inflow / Borrowing", fin=True)
        if SALARY_RX.search(narr) and crd >= 5000:
            return out("SALARY", "Payroll / Wages", rev=True)
        if INTEREST_RX.search(narr) or re.search(r"INTEREST", narr, re.I):
            return out("INTEREST_INCOME", "Bank / Investment Interest")
        # a payout comes FROM an insurer; 'LIC PREMI' in a person's remark is a
        # reimbursement of a premium, not a claim
        if INSURANCE_RX.search(cp) or re.search(r"INSURANCE|ASSURANCE", cp, re.I):
            return out("INSURANCE_PAYOUT", "Insurance Claim / Maturity (Non-Operating)")
        if CASH_RX.search(narr) or cp == "Cash":
            if any(k in narr.upper() for k in ("SALE", "INVOICE", "BILL", "COLLECTION", "CUSTOMER")):
                return out("BUSINESS_RECEIPT", "Cash Sales / Verified Counter Receipt", rev=True)
            return out("CASH_DEPOSIT", "Branch Counter / CDM Cash Deposit")
        if INVESTMENT_RX.search(narr):
            return out("INVESTMENT_RETURN", "Securities / MF Redemption")
        if TAX_RX.search(narr) and "REFUND" in narr.upper():
            return out("TAX_REFUND", "Income Tax / GST Refund")
        if _PERSONAL_LOAN_RX.search(narr) and _is_party(cp):
            return out("PERSONAL_LOAN_CR", "Money Borrowed from / Repaid by an Individual (Non-Operating)")
        if _is_party(cp):
            return out("BUSINESS_RECEIPT", "Trade Inflow / Customer Payment", rev=True)
        if channel == "CHEQUE" or re.search(r"\bCLG\b|CLEARING", narr, re.I):
            return out("BUSINESS_RECEIPT", "Cheque Collection (Drawer Not Printed)", rev=True)
        return out("UNCLASSIFIED_CR", "Unidentified Inflow (No Party / Rule Match)")

    # ----------------------------------------------------------------------
    # Debits
    # ----------------------------------------------------------------------
    if is_self:
        return out("SELF_TRANSFER_DR", "Own Account Transfer", contra=True)
    if REVERSAL_DR_RX.search(narr):
        # 'WRNG CASH AMT ENTERD NOW REV': the bank undoing its own posting
        cp = "Bank"
        return out("REVERSAL_DR", "Reversal of a Wrong Credit")
    if CREDIT_CARD_RX.search(narr):
        # a card bill pays for purchases already made: spending, not debt service
        return out("CREDIT_CARD_PAYMENT", "Card Bill Repayment", op=True)
    loan_account = LOAN_ACCOUNT_RX.search(narr) or any(a in narr for a in holder.loan_accounts)
    # a lender named as the PAYEE is an EMI on any channel ('UPI/DR/…/BAJAJ FINA/…/BAJAJFINANCEL');
    # a lender mentioned only in a UPI remark is not
    payee_lender = match_lender(cp) or match_lender(_upi_handle(narr) or "")
    mandate_to_lender = MANDATE_RX.search(narr) and (
        lender or BANK_LENDER_RX.search(narr)
        or re.search(r"FIN(?:ANCE|VEST|CORP|SERV)?\b|CREDIT|CAPITAL|LOAN", narr, re.I))
    # A UPI remark saying 'LOAN' is not an EMI unless a lender is named
    keyword_emi = EMI_RX.search(narr) and deb >= 500 and (channel != "UPI" or lender)
    if loan_account or mandate_to_lender or (lender and channel != "UPI") or keyword_emi or payee_lender:
        if lender or payee_lender:
            cp = lender or payee_lender
        closure = LOAN_CLOSED_RX.search(narr)
        return out("LOAN_EMI", "Loan Payoff / Closure" if closure else "Loan Installment Repayment", fin=True)
    if _PERSONAL_LOAN_RX.search(narr) and _is_party(cp):
        # '…/MISS DHAN/…/1K LOAN': lending to a person is not a business expense
        return out("PERSONAL_LOAN_DR", "Money Lent to an Individual (Non-Operating)")
    if INTEREST_RX.search(narr):
        return out("INTEREST_EXPENSE", "OD / CC / Loan Interest", fin=True)
    # a fee is posted by the bank; a payment the customer made with the word
    # 'CHARGES' in its remark ('…-HIRING CHARGES') is not one
    # decided by how the row is printed: '<account>-<remark>' or a payment
    # channel the customer drives. A name parsed out of a fee description
    # ('CERSAI CHARGES …RAKESH KANTILAL JAIN') does not make it the customer's.
    customer_initiated = bool(CUSTOMER_REMARK_RX.match(narr) or _CUSTOMER_CHANNEL_RX.match(narr))
    if PENALTY_RX.search(narr) and not customer_initiated:
        return out("BANK_CHARGES", "Penal Charge", op=True)
    if re.search(r"LIEN\s*MARKING|MANDATE|MMSREG", narr, re.I) and not customer_initiated:
        # a lien / mandate fee says nothing on its own about a payment bouncing
        return out("BANK_CHARGES", "Mandate / Lien Charge", op=True)
    if (SERVICE_CHARGE_RX.search(narr) and not customer_initiated) or cp == "Bank":
        return out("BANK_CHARGES", "Service Charge", op=True)
    if TAX_RX.search(narr) or cp == "Tax Authority":
        return out("TAX_GST", "Direct / Indirect Tax Payment")
    if UTILITY_RX.search(narr) and not (channel == "UPI" and not re.search(r"BILL|BBPS|RECHARGE", narr, re.I)):
        return out("UTILITY_BILL", "Power / Telecom / Water", op=True)
    if RENT_RX.search(narr) or _GLUED_RENT_RX.search(narr):
        return out("RENT_EXPENSE", "Commercial / Residential Rent", op=True)
    if INSURANCE_RX.search(narr):
        return out("INSURANCE_PREMIUM", "Life / General Insurance", op=True)
    if CASH_RX.search(narr) or cp == "Cash":
        return out("CASH_WITHDRAWAL", "ATM / Counter Cash Withdrawal", op=True)
    if INVESTMENT_RX.search(narr):
        return out("INVESTMENT_OUTFLOW", "Mutual Fund / Equity / Sweep")
    if _BBPS_RX.search(narr):
        return out("BILL_PAYMENT", "BBPS Bill Payment (Biller Not Printed)", op=True)
    if _WALLET_RX.search(narr):
        return out("WALLET_TOPUP", "Money Loaded into a Wallet", op=True)
    if _is_party(cp):
        return out("BUSINESS_EXPENSE", "Supplier / Vendor / Opex Payment", op=True)
    if CUSTOMER_REMARK_RX.match(narr):
        return out("BUSINESS_EXPENSE", "Customer Payment (Payee Not Printed)", op=True)
    # kept in expenses (the conservative side) but reported as unidentified
    return out("UNCLASSIFIED_DR", "Unidentified Outflow (No Party / Rule Match)", op=True)


# Own deposits paying out ('0402501051314 : Closure Proceeds'): the account is the holder's
_OWN_DEPOSIT_PAYOUT_RX = re.compile(r"CLOSURE\s*PROCEEDS|MATURITY|PRE-?MATURE|\bRD\b.*\bCLOS|\bFD\b.*\bCLOS", re.I)


def _learn_own_accounts(txns: list[dict], holder: Holder) -> None:
    """An account number printed next to the holder's own name is theirs
    ('IMPERATIVE BUSINESS VENTURES PVT LTD-12165010107' → 'OD- 12165010107')."""
    for t in txns:
        narr = t.get("narration") or ""
        named = t.get("party_hint") or extract_counterparty(narr)
        if holder.name and _is_party(named) and same_party(named, holder.name):
            holder.own_accounts |= _own_accounts_in(narr, holder, t.get("reference") or "")
            if t.get("party_account"):
                holder.own_accounts.add(t["party_account"])
        # a deposit that pays 'closure proceeds' back to the holder was theirs,
        # so the monthly debits into it were own-account transfers too
        if t.get("credit") and _OWN_DEPOSIT_PAYOUT_RX.search(narr):
            holder.own_accounts |= {a for a in re.findall(r"(?<!\d)(\d{9,18})(?!\d)", narr) if a != holder.account}
        # loan accounts named anywhere, so a later 'Payoff' row is recognised
        m = LOAN_ACCOUNT_RX.search(narr)
        if m:
            holder.loan_accounts.add(m.group(1))
    holder.own_accounts -= holder.loan_accounts


# Remarks the customer types for money moving inside the family or group
_FAMILY_REMARK_RX = re.compile(r"/FAMILY/|\bFAMILY\b|\bFAMILY\s*MAINT", re.I)
_INTERNAL_REMARK_RX = re.compile(r"\bTPT\W+INTERNAL\b|\bINTERNAL\s*(?:TRF|TRANSFER)?\s*$|-INTERNAL\b", re.I)
# Same-bank internal transfers that print only the other account
_INTERNAL_CHANNEL_RX = re.compile(r"^eTXN/|\bTPT\b|^FT\s*-|\bIB~?\s*BY\s*TRF\b", re.I)


def _party_text(rows: list[dict]) -> str:
    """Everything printed about one party: names, UPI handles, remarks."""
    return " ".join(f"{t.get('narration') or ''} {t.get('reference') or ''}" for t in rows).upper()


def _common_name_tokens(rows_by_cp: dict) -> set[str]:
    """Name words too common in THIS statement to tie two people together:
    ones that turn up inside the names or handles of many unrelated parties
    (BoB 'KUMAR' in dozens of VPAs). Learned from the data, not a list."""
    compacts = [re.sub(r"[^A-Z]", "", norm_name(cp)) for cp in rows_by_cp]
    threshold = max(5, int(0.02 * len(compacts)))
    tokens = {w for cp in rows_by_cp for w in norm_name(cp).split() if len(w) >= 4 and w.isalpha()}
    return {w for w in tokens if sum(1 for c in compacts if w in c) >= threshold}


def _related_parties(classified: list[dict], holder: Holder) -> tuple[dict[str, str], set[int]]:
    """Possible related parties: ({party: why}, individual rows).

    Party-level signals (every row with the party):
    - Business holder: the other firm shares the holder's distinctive first
      word ('TANMAY TRADELINKS LLP' for 'TANMAY INTERNATIONAL').
    - Group name: a word in the holder's email used as a surname by a party
      and shared by others ('vasaexport@gmail.com': GUNVANT S VASA, VASA
      STEELS, GUNAVANT S VASAHUF).
    - Individual holder: a party carrying one of the holder's other names in
      its name or UPI handle ('AKSHATASAKPAL'), with money both ways.
    - The person the holder lives care of ('C/O USMAN YASIN SHAIKH').
    - Unnamed same-bank transfers to a sibling of an account already tied to
      a related party.
    - A masked account used in both directions.

    Row-level signals (only that transaction): the customer's own remark
    says 'FAMILY' or 'INTERNAL'. One account can take both an INTERNAL
    transfer and a HIRING payment; only the first is group money.
    """
    rows_by_cp = defaultdict(list)
    for i, t in enumerate(classified):
        cp = t.get("counterparty") or ""
        if t.get("is_contra") or t.get("reversal_pair") or not _is_party(cp) or t["category"].startswith("LOAN"):
            continue
        rows_by_cp[cp].append((i, t))

    related_rows = {i for rows in rows_by_cp.values() for i, t in rows
                    if _FAMILY_REMARK_RX.search(t.get("narration") or "")
                    or _INTERNAL_REMARK_RX.search(t.get("narration") or "")}

    common = _common_name_tokens(rows_by_cp)
    related = _group_name_parties(rows_by_cp, holder)
    why = {cp: "Group Name in Holder's Email" for cp in related}

    def add(cp, reason):
        related.add(cp)
        why.setdefault(cp, reason)
    # accounts of holders who share this holder's contact details (earlier statements)
    for cp, pairs in rows_by_cp.items():
        text = _party_text([t for _, t in pairs])
        for link in holder.linked:
            if (link["account_number"] and link["account_number"] in text) or \
                    (link.get("customer_name") and same_party(cp, link["customer_name"])):
                add(cp, "Holder Linked by Shared Contact Details")
    for cp, pairs in rows_by_cp.items():
        rows = [t for _, t in pairs]
        n_in = sum(1 for t in rows if t.get("credit"))
        n_out = len(rows) - n_in
        if cp.startswith("A/c XXXX") and n_in and n_out:
            add(cp, "Masked Account Used Both Ways")
            continue
        if any(same_party(cp, c) for c in holder.care_of):
            add(cp, "Holder's Care-Of Name")
            continue
        toks = norm_name(cp).split()
        if not toks:
            continue
        # a firm by its name or by its account (borrower type): family names
        # are an individual's, and a firm's name is not one
        if holder.is_business or getattr(holder, "borrower_type", "") == "BUSINESS":
            if holder.first_token and toks[0] == holder.first_token:
                add(cp, "Shares the Holder's Firm Name")
        elif holder.family_tokens and n_in and n_out:
            # which token is the first name varies by bank ('THORVE SURESH VASANT'
            # prints the surname first), so every name counts. The holder's own
            # name printed as the beneficiary ('…-KRISHNA LOGISTICS-SAHYADRI AGRO
            # FOODS-N…') is not a relative's, so it is taken out first
            compact = re.sub(r"[^A-Z]", "", _party_text(rows))
            own = re.sub(r"[^A-Z]", "", holder.name.upper())
            if own:
                compact = compact.replace(own, "")
            for fam in holder.family_tokens - common:
                # truncated ('SAKIB USM' for USMAN), or glued into a handle
                # ('thorveshashi01', 'AKSHATASAKPAL'); a glued match needs a
                # longer name, since a short one turns up inside unrelated handles
                if (len(fam) >= 6 and fam in compact) or \
                        any(len(w) >= 3 and fam.startswith(w) for w in toks[1:]):
                    add(cp, "Shares a Holder's Family Name")
                    break

    # Sibling accounts: same bank, same branch prefix as a related account
    linked = {a for cp in related for _, t in rows_by_cp.get(cp, [])
              for a in re.findall(r"(?<!\d)(\d{12,18})(?!\d)", t.get("narration") or "")}
    prefixes = {(len(a), a[:len(a) - 5]) for a in linked if a != holder.account}
    for cp, pairs in rows_by_cp.items():
        m = re.fullmatch(r"A/c (\d{12,18})", cp)
        if m and (len(m.group(1)), m.group(1)[:len(m.group(1)) - 5]) in prefixes and \
                all(_INTERNAL_CHANNEL_RX.search(t.get("narration") or "") for _, t in pairs):
            add(cp, "Sibling Account of a Related Party")
    return why, related_rows


def _group_name_parties(rows_by_cp: dict, holder: Holder) -> set[str]:
    """Parties sharing a family / group name that also appears in the holder's
    own email ('vasaexport@gmail.com' for VIDHI SALES CORPORATION).

    A word counts as a group name only if some party uses it as a surname
    (the last word of an individual's name: 'GUNVANT S VASA') and it recurs
    in at least one more party. Trade words in an email ('export', 'sales')
    are never anyone's surname, so no word list is needed. Once established
    it also matches with a suffix glued on ('GUNAVANT S VASAHUF' = Vasa HUF)."""
    if len(holder.email_local) < 4:
        return set()
    by_token: dict[str, set[str]] = defaultdict(set)
    surnames = set()
    for cp in rows_by_cp:
        words = norm_name(cp).split()
        for w in set(words):
            if len(w) >= 4 and w.isalpha() and w.lower() in holder.email_local:
                by_token[w].add(cp)
        if _is_person(cp) and words:
            surnames.add(words[-1])
    groups = {w for w, cps in by_token.items() if len(cps) >= 2 and w in surnames}
    return {cp for cp in rows_by_cp
            if any(w.startswith(g) for w in norm_name(cp).split() for g in groups)}


_PAYROLL_REMARK_RX = re.compile(r"\bSALAR(?:Y|IES)\b|\bWAGES?\b|\bPAYROLL\b|\bSTIPEND\b|\bBONUS\b", re.I)
_PAYROLL_OPEN = ("BUSINESS_EXPENSE", "UNCLASSIFIED_DR")


def _is_person(cp: str) -> bool:
    """'PANKAJ VIJAY GUPTA' is a person; 'PAVITRA INFOTECH', 'VPA …', 'A/c …' are not."""
    if not _is_party(cp) or cp.startswith(("VPA ", "A/c ", "Loan A/c")):
        return False
    words = norm_name(cp).split()
    return 2 <= len(words) <= 4 and all(w.isalpha() for w in words) and not _BUSINESS_NAME_RX.search(cp)


def _mark_payroll(classified: list[dict], holder: Holder) -> dict[str, str]:
    """Salaries leave in pay runs: one or two peak days a month on which a
    business pays many individuals at once. Rules are relative to the
    statement itself, so no amount or name list is needed:

    - A pay-run day pays at least half as many individuals as the busiest
      day (and 5+). Days with a handful of payments are vendor batches.
    - Only payments made ON pay-run days are payroll; a person paid on
      pay-run days in 2+ months is an employee.
    - A payment over 5x the pay run's median is not a salary (vendors paid
      the same day, ₹4.9L against a ₹13k norm).
    - Individuals paid like that who share a surname are returned as
      possible related parties (directors / family: the Paithankars).
    - A debit whose remark says SALARY / WAGES is payroll outright.

    Only a business runs payroll, and not over UPI.
    """
    persons_by_day = defaultdict(list)
    if holder.is_business or getattr(holder, "borrower_type", "") == "BUSINESS":
        for t in classified:
            if (t.get("debit") and t.get("txn_date") and t["category"] in _PAYROLL_OPEN
                    and _is_person(t["counterparty"]) and detect_channel(t.get("narration") or "") != "UPI"):
                persons_by_day[t["txn_date"]].append(t)
    counts = {d: len({t["counterparty"] for t in ts}) for d, ts in persons_by_day.items()}
    peak = max(counts.values(), default=0)
    run_days = {d for d, n in counts.items() if n >= max(5, 0.5 * peak)}
    run_rows = [t for d in run_days for t in persons_by_day[d]]
    run_median = statistics.median(float(t["debit"]) for t in run_rows) if run_rows else 0.0
    cap = 5 * run_median

    # judge each payee on their typical pay-run payment, not payment by payment:
    # a vendor paid ₹1.5L on most runs is not an employee for its ₹20k one
    by_payee = defaultdict(list)
    for t in run_rows:
        by_payee[t["counterparty"]].append(t)
    employees, big = set(), set()
    for cp, ts in by_payee.items():
        if statistics.median(float(t["debit"]) for t in ts) > cap:
            big.add(cp)
        elif len({t["txn_date"].strftime("%Y-%m") for t in ts}) >= 2:
            employees.add(cp)

    for t in classified:
        if not t.get("debit") or t["category"] not in _PAYROLL_OPEN:
            continue
        on_run = (t.get("txn_date") in run_days and t["counterparty"] in employees
                  and float(t["debit"]) <= cap)
        if on_run or _PAYROLL_REMARK_RX.search(t.get("narration") or ""):
            t.update(category="PAYROLL", subcategory="Salaries / Wages", is_operating_expense=True)

    # large pay-run payees sharing a surname: likely directors or family, and
    # so is anyone else paid who carries that surname
    by_surname = defaultdict(set)
    for cp in big:
        by_surname[norm_name(cp).split()[-1]].add(cp)
    family = {s for s, cps in by_surname.items() if len(cps) >= 2}
    # they share a surname with each other, not necessarily with the holder
    return {t["counterparty"]: "Shared Surname Among Large Payees" for t in classified
            if _is_person(t.get("counterparty") or "") and norm_name(t["counterparty"]).split()[-1] in family}


_HANDLE_RX = re.compile(r"([A-Za-z0-9._\-]{6,})@|/([A-Za-z][A-Za-z0-9._\-]{5,})\s*$")


def _upi_handle(narration: str) -> str | None:
    """The payer's UPI handle, unmasked ('AKSHATASAKPAL', 'nk2864266@ybl').
    Masked handles ('**HAIKH@IBL') and payment hashes identify no one."""
    n = narration or ""
    if not re.match(r"^UPI", n, re.I) or "*" in n.split("@")[0][-8:]:
        return None
    m = _HANDLE_RX.search(n)
    h = (m.group(1) or m.group(2)) if m else None
    if not h or re.fullmatch(r"[0-9A-F]{16,}", h.upper()):
        return None
    return h.upper()


def _unify_by_handle(classified: list[dict]) -> None:
    """One UPI handle is one payer, whatever display name the bank prints
    (Bandhan: 'MRS SUNAND' pays from AKSHATASAKPAL). Rows sharing a handle
    take the handle's most frequent name."""
    names = defaultdict(lambda: defaultdict(int))
    for t in classified:
        h = _upi_handle(t.get("narration"))
        if h and _is_party(t.get("counterparty") or ""):
            names[h][t["counterparty"]] += 1
    for t in classified:
        h = _upi_handle(t.get("narration"))
        if h and len(names.get(h, {})) > 1:
            t["counterparty"] = max(names[h].items(), key=lambda kv: kv[1])[0]


_RAIL_RX = re.compile(r"\b(?:RTGS|NEFT|IMPS)", re.I)


def _pair_reversals(classified: list[dict]) -> None:
    """A reversal credit undoes an earlier debit: pair them by the shared
    transaction number ('UPI/DR/D412798989106' ↔ 'UPI/REV/R412798989106'),
    or else by amount and party within 3 days. Both drop out of expenses,
    counterparty totals and pass-through checks."""
    def ids(t):
        return set(re.findall(r"(?<!\d)(\d{9,})(?!\d)", f"{t.get('narration') or ''} {t.get('reference') or ''}"))
    for i, t in enumerate(classified):
        # Canara prints the receiver on a reversal ('UPI/REV/432062501645/SOHEB
        # USM'), so it can read as an own transfer: it is still a reversal when
        # it carries the transaction number of an equal earlier debit
        by_id_only = t["category"] == "SELF_TRANSFER_CR"
        if not t.get("credit") or t["category"] not in ("REFUND_REVERSAL", "SELF_TRANSFER_CR") \
                or t.get("reversal_pair"):
            continue
        amt, mine = float(t["credit"]), ids(t)
        for j in range(i - 1, -1, -1):
            d = classified[j]
            if t.get("txn_date") and d.get("txn_date") and (t["txn_date"] - d["txn_date"]).days > 10:
                break
            if not d.get("debit") or d.get("reversal_pair") or abs(float(d["debit"]) - amt) >= 0.5:
                continue
            near = t.get("txn_date") and d.get("txn_date") and (t["txn_date"] - d["txn_date"]).days <= 3
            # a returned RTGS/NEFT/IMPS prints its own UTR and no payee: pair it
            # with the outgoing transfer of that amount on the same rail
            rail = _RAIL_RX.search(t.get("narration") or "")
            same_rail = rail and re.search(rf"\b{rail.group(0)}", d.get("narration") or "", re.I)
            if by_id_only and not (mine & ids(d)):
                continue
            if (mine & ids(d)) or (near and (d.get("counterparty") == t.get("counterparty")
                                            or (same_rail and not _is_party(t.get("counterparty") or "")))):
                if by_id_only:
                    t.update(category="REFUND_REVERSAL", subcategory="Refund / Reversal / Cashback",
                             is_contra=False, is_revenue=False)
                t["reversal_pair"] = d["reversal_pair"] = True
                d.update(category="REVERSED_DEBIT", subcategory="Debit Later Reversed",
                         is_operating_expense=False)
                if _is_party(d.get("counterparty") or ""):
                    t["counterparty"] = d["counterparty"]
                break


def _mark_bank_inflows(classified: list[dict]) -> None:
    """Money paid in BY a bank (RTGS from 'RBL BANK', NEFT from 'PMC BANK') is
    not shown to be a customer paying an invoice: it may be a loan, an OD, an
    own-account move or a remittance. It is held out of income, and its
    purpose is named only on evidence: money later paid back to the same bank
    makes it probable financing; otherwise it is UNKNOWN, for review."""
    for i, t in enumerate(classified):
        if not (t.get("credit") and t["category"] == "BUSINESS_RECEIPT"
                and re.search(r"\bBANK\b", t["counterparty"] or "", re.I)):
            continue
        repaid = [d for d in classified[i + 1:] if d.get("debit") and _is_party(d.get("counterparty") or "")
                  and same_party(d["counterparty"], t["counterparty"])]
        if repaid:
            t.update(purpose="LOAN / FINANCING (probable)",
                     purpose_evidence=f"{len(repaid)} later payment(s) back to the same bank",
                     subcategory="Paid in by a Bank — Probable Financing (paid back to it later)")
        else:
            t.update(purpose="UNKNOWN",
                     purpose_evidence="no loan wording, no repayment to it, not an own account, no customer named",
                     subcategory="Paid in by a Bank — Purpose Unknown (Review)")
        t.update(category="BANK_FUNDED_INFLOW", is_revenue=False)


def _mark_pass_through(classified: list[dict]) -> None:
    """The same party's money in and straight back out (same amount ±1%,
    within 7 days: HDFC 'MNK AND CO' ₹18.3L in, 'MNK & CO.' ₹18.3L out) is
    neither earned income nor an operating cost. Both legs leave the income
    and expense figures; the pair is still reported as a pass-through."""
    dated = [t for t in classified if t.get("txn_date")]
    for i, c in enumerate(dated):
        if not c.get("credit") or c["category"] != "BUSINESS_RECEIPT" or not _is_party(c["counterparty"] or ""):
            continue
        amt = float(c["credit"])
        for d in dated[i + 1:]:
            if (d["txn_date"] - c["txn_date"]).days > 7:
                break
            if (d.get("debit") and d["category"] == "BUSINESS_EXPENSE" and not d.get("pass_through")
                    and abs(float(d["debit"]) - amt) <= 0.01 * amt and same_party(c["counterparty"], d["counterparty"])):
                c.update(category="PASS_THROUGH_CR", is_revenue=False, pass_through=True,
                         subcategory="Received and Paid Back Out (Pass-Through)")
                d.update(category="PASS_THROUGH_DR", is_operating_expense=False, pass_through=True,
                         subcategory="Received and Paid Back Out (Pass-Through)")
                break


def _match_loan_instalments(classified: list[dict]) -> None:
    """An EMI paid on another channel when the mandate failed (BoB: Fullerton
    ACH return on 05-Aug, then ₹5,343 by BBPS bill-pay on 17-Aug). A debit
    of exactly a lender's recurring instalment, within 35 days of that
    lender's other payments, is that loan's EMI."""
    by_lender = defaultdict(list)
    for t in classified:
        if t.get("debit") and t["category"] == "LOAN_EMI" and t.get("txn_date"):
            by_lender[t["counterparty"]].append(t)
    instalments = {}
    for lender, ts in by_lender.items():
        counts = defaultdict(list)
        for t in ts:
            counts[round(float(t["debit"]), 2)].append(t["txn_date"])
        for amt, days in counts.items():
            if len(days) >= 2 and amt >= 1000:
                instalments[amt] = (lender, days)
    for t in classified:
        if not t.get("debit") or not t.get("txn_date") or t["category"] not in (
                "BILL_PAYMENT", "BUSINESS_EXPENSE", "UNCLASSIFIED_DR"):
            continue
        amt = round(float(t["debit"]), 2)
        hit = instalments.get(amt)
        # round figures (₹3,000) recur by chance; an exact odd amount (₹5,343) or
        # a bill-pay to an unnamed biller is evidence of the same instalment
        distinctive = t["category"] == "BILL_PAYMENT" or amt % 100 != 0
        if hit and distinctive and min(abs((t["txn_date"] - d).days) for d in hit[1]) <= 35:
            t.update(category="LOAN_EMI", counterparty=hit[0], is_financing=True, is_operating_expense=False,
                     subcategory="EMI Paid on Another Channel (Matched by Amount)")


def classify_all_transactions(txns: list[dict], customer_name: str = "", info: dict | None = None) -> list[dict]:
    """Annotate every transaction with its category classification."""
    info = info or {}
    joint = [j.strip() for j in re.split(r"[/,;]", str(info.get("joint_holder") or "")) if j.strip()]
    holder = Holder(customer_name or info.get("customer_name") or "", info.get("account_number") or "", joint,
                    str(info.get("email") or ""), str(info.get("mobile") or ""))
    holder.linked = list(info.get("linked_accounts") or [])
    # a firm by its name, or by its account (current / OD) when the name is
    # missing or personal (a proprietor); see account_type.resolve_borrower_type.
    # Used only to decide whether receipts from individuals are customers.
    holder.borrower_type = info.get("borrower_type") or ("BUSINESS" if holder.is_business else
                                                         "INDIVIDUAL" if holder.name else "UNKNOWN")
    m = re.match(r"^\s*C\s*/?\s*O\.?\s+((?:[A-Z]+\s+){1,3}[A-Z]+)", str(info.get("address") or ""))
    if m:
        # the first two or three words after C/O are the name; the rest is street
        holder.care_of = [" ".join(m.group(1).split()[:3])]
    _learn_own_accounts(txns, holder)

    classified = []
    for t in txns:
        item = dict(t)
        item.update(classify_transaction(t, customer_name, holder))
        classified.append(item)
    _unify_by_handle(classified)
    _pair_reversals(classified)

    # Returns: which side bounced is decided by the money, not the wording
    for i, r in find_returns(classified).items():
        item = classified[i]
        # a return row is either the bank's charge for it or the payment itself
        item["return_is_charge"] = bool(r.get("is_charge"))
        if r["side"] == "DEPOSIT":
            item.update(category="DEPOSIT_RETURN", subcategory="Deposited Cheque Dishonoured (Payer Bounced)",
                        is_operating_expense=False, is_revenue=False, bounce_side="DEPOSIT")
            m = r.get("matched")
            if m is not None and classified[m].get("credit"):
                classified[m].update(category="RETURNED_DEPOSIT", is_revenue=False,
                                     subcategory="Deposit Later Returned Unpaid")
        elif r["side"] == "OWN":
            if item.get("debit") and not r.get("reversed"):
                item.update(category="BOUNCE_PENALTY", subcategory="Own Cheque / Mandate Return Charge",
                            is_operating_expense=False, bounce_side="OWN")
            else:
                item["bounce_side"] = "OWN"
        else:
            item.update(category="BOUNCE_PENALTY", subcategory="Return (Side Unresolved)",
                        is_operating_expense=False, bounce_side="UNRESOLVED")

    related, related_rows = _related_parties(classified, holder)
    _tag_related(classified, related, related_rows)
    # payroll runs after: family money is not salary. Large same-surname
    # pay-run payees it finds go back through the related-party tagging.
    _tag_related(classified, _mark_payroll(classified, holder), set(),
                 cats=("BUSINESS_EXPENSE", "UNCLASSIFIED_DR", "BUSINESS_RECEIPT", "UNCLASSIFIED_CR", "PAYROLL"))
    _mark_bank_inflows(classified)
    _mark_pass_through(classified)
    _match_loan_instalments(classified)
    _mark_personal_credits(classified, holder)
    # who each party is, decided once from all its rows (see entities.py);
    # last, so every category it reads is final
    assign_entities(classified)
    return classified


# What an organisation's name is made of: legal forms and the nouns
# organisations are named by. Matched as word prefixes, so truncated names
# still count ('NATIONAL SKILL DEVELOPMENT CORPORATI'). Language knowledge
# about names in general, not a list of particular parties.
_ORG_WORD_RX = re.compile(
    r"\b(?:PVT|PRIVATE|LTD|LIMI|LLP|INC\b|CORPORAT|COMPANY|ENTERPRIS|INDUSTR|CONSTRUCT|ENGINEER|TECHNO|"
    r"INFOTECH|SOFTWARE|SYSTEM|SOLUTION|SERVICE|LOGISTIC|TRANSPORT|TRAVEL|PHARMA|MEDICAL|HOSPITAL|CLINIC|"
    r"FOODS|HOTEL|MOTORS|TEXTILE|CHEMICAL|ELECTRIC|BUILDER|DEVELOPMENT|DEVELOPER|REALTY|ESTATE|FINANCE|"
    r"CAPITAL|INSURANCE|ASSURANCE|MARKETING|CONSULT|AGENC|TRADER|TRADING|EXPORT|IMPORT|MANUFACTUR|"
    r"FOUNDATION|TRUST|SOCIETY|ASSOCIATION|SCHOOL|COLLEGE|UNIVERSITY|ACADEMY|INSTITUT|MISSION|COUNCIL|"
    r"GOVT|GOVERNMENT|MUNICIPAL|DEPARTMENT|BOARD\b|BANK\b)", re.I)


def _is_organisation(t: dict) -> bool:
    """The payer is an organisation: its name says so, or it is a single
    word paid in over a bank-to-bank rail (people are printed with at least
    two names on NEFT/RTGS/IMPS: 'OASYS' is a company)."""
    cp = t.get("counterparty") or ""
    if _ORG_WORD_RX.search(cp) or _BUSINESS_NAME_RX.search(cp):
        return True
    words = norm_name(cp).split()
    return (len(words) == 1 and words[0].isalpha() and len(words[0]) >= 4
            and not cp.startswith(("VPA ", "Mobile ", "A/c ")) and bool(_RAIL_RX.search(t.get("narration") or "")))


def _recurring_payers(receipts: list[dict]) -> set[str]:
    """Payers with a salary-like rhythm: 3+ payments of nearly the same amount
    (±5%) about a month apart (25-35 days). Repeated personal transfers of
    varying size are not a regular income."""
    by_cp = defaultdict(list)
    for t in receipts:
        if t.get("txn_date") and float(t["credit"]) >= 1000:
            by_cp[t["counterparty"]].append(t)
    out = set()
    for cp, ts in by_cp.items():
        ts.sort(key=lambda t: t["txn_date"])
        for i, first in enumerate(ts):
            run, amt = [first], float(first["credit"])
            for t in ts[i + 1:]:
                gap = (t["txn_date"] - run[-1]["txn_date"]).days
                if 25 <= gap <= 35 and abs(float(t["credit"]) - amt) <= 0.05 * amt:
                    run.append(t)
            if len(run) >= 3:
                out.add(cp)
                break
    return out


def _mark_personal_credits(classified: list[dict], holder: Holder) -> None:
    """An individual's account receiving money from other individuals: the
    statement shows who paid, not why (a client's fee, a friend repaying, a
    family transfer). Such a credit is UNKNOWN — held out of verified income
    and listed for review — unless the payer's own pattern is evidence of
    income:
    - the same amount (±5%) roughly monthly, 3+ times (_recurring_payers), or
    - payments in 3+ different months, money only ever flowing in (two-way
      flows between two people are settling up, not income).
    Payments from businesses (an employer, NSDC) are not affected; nor is an
    account whose holder is a firm, or whose holder could not be identified
    (unknown is not 'individual')."""
    # a firm's receipts from individuals are its customers paying; for an
    # individual, or a holder who could not be identified, they are unknown
    if holder.is_business or holder.borrower_type == "BUSINESS":
        return
    receipts = [t for t in classified if t["category"] == "BUSINESS_RECEIPT" and t.get("credit")]
    recurring = _recurring_payers(receipts)
    total = sum(float(t["credit"]) for t in receipts)
    from_firms = sum(float(t["credit"]) for t in receipts if _is_organisation(t))
    if total and from_firms / total >= 0.5:
        return
    months = defaultdict(set)
    for t in receipts:
        if t.get("txn_date"):
            months[t["counterparty"]].add(t["txn_date"].strftime("%Y-%m"))
    paid_to = {t["counterparty"] for t in classified if t.get("debit") and _is_party(t.get("counterparty") or "")}
    # spacing dropped by the bank ('SHIREEN U' = 'Shireenu'); digits kept, so
    # 'VPA 8766918602' and 'VPA 9284306930' stay two payers
    compact = lambda n: re.sub(r"[^A-Z0-9]", "", (n or "").upper())
    paid_compact = {compact(o) for o in paid_to}

    def paid_back(cp):
        return compact(cp) in paid_compact or any(same_party(cp, o) for o in paid_to)
    regular = {cp for cp, ms in months.items() if len(ms) >= 3 and _is_party(cp) and not paid_back(cp)}
    for t in receipts:
        if _is_organisation(t) or t["counterparty"] == "Cash":
            continue
        if t["counterparty"] in recurring:
            t["subcategory"] = "Recurring Payer (same amount, monthly) — Counted as Income"
            continue
        if t["counterparty"] in regular:
            t["subcategory"] = "Regular One-Way Payer (3+ months) — Counted as Income"
            continue
        t.update(category="UNKNOWN_PERSONAL_CR", is_revenue=False,
                 subcategory="Credit from an Individual — Purpose Unknown (Review)")
    # spending from a personal account is not a business's vendor payment;
    # the category stays (it is still an outflow) but the label says what it is
    for t in classified:
        if t.get("debit") and t["category"] == "BUSINESS_EXPENSE":
            t["subcategory"] = "Payment to Person / Merchant (Personal Account)"


def _tag_related(classified, parties, rows, cats=("BUSINESS_RECEIPT", "BUSINESS_EXPENSE",
                                                    "UNCLASSIFIED_CR", "UNCLASSIFIED_DR")):
    """`parties`: {party: why it is possibly related}, or a set (reason given by caller)."""
    for i, item in enumerate(classified):
        if (item.get("counterparty") in parties or i in rows) and item["category"] in cats:
            cr = bool(item.get("credit"))
            reason = parties.get(item.get("counterparty")) if isinstance(parties, dict) else None
            item.update(category="RELATED_PARTY_CR" if cr else "RELATED_PARTY_DR",
                        subcategory="Possible Related Party (Customer Remark)" if i in rows
                        else f"Possible Related Party ({reason or 'Name Match'})",
                        is_revenue=False, is_operating_expense=False)
