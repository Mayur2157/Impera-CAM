"""Excel writer: Financial Profile / Income Analysis / Transactions / Customer_Info / Validation.

Produces an institutional-grade Credit Appraisal & Financial Analysis workbook
with 10 dedicated worksheets, formatted ratios, scorecards, and audit logs.
"""
from __future__ import annotations

from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.analysis.profiler import generate_financial_profile
from app.core.validate import validate_field_linkage

# Palette
HDR_FILL = PatternFill("solid", fgColor="1F3864")       # Deep Navy
HDR_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
SUB_HDR_FILL = PatternFill("solid", fgColor="2F5597")   # Medium Navy
SUB_HDR_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
SEC_FILL = PatternFill("solid", fgColor="D9E1F2")       # Soft Blue Accent
SEC_FONT = Font(name="Arial", size=10, bold=True, color="1F3864")
BODY = Font(name="Arial", size=10)
BODY_BOLD = Font(name="Arial", size=10, bold=True)
WARN = PatternFill("solid", fgColor="FFF2CC")           # Light Amber
BAD = PatternFill("solid", fgColor="F8CBAD")            # Light Red
GOOD = PatternFill("solid", fgColor="E2EFDA")           # Soft Mint Green
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)

TXN_COLS = [
    ("S.No", 7), ("Txn Date", 12), ("Value Date", 12), ("Narration", 70),
    ("Reference", 20), ("Debit", 15), ("Credit", 15), ("Balance", 17),
    ("Type", 8), ("Category", 22), ("Counterparty", 25),
    # who (one per counterparty) and why (per transaction), kept apart
    ("Counterparty ID", 22), ("Relationship", 16), ("Purpose", 30),
    ("Page", 6), ("Status", 10)
]



def _fmt_or_na(v, fmt):
    """A figure the statement does not support (e.g. no printed OD limit) shows as N/A, not 0."""
    return fmt.format(v) if v is not None else "N/A — limit not printed in statement"

def _f(v):
    return float(v) if isinstance(v, Decimal) else v


def _style_header(ws, row=1, fill=HDR_FILL, font=HDR_FONT):
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.font = fill, font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def write_workbook(path, txns, info, issues, meta, profile=None):
    if profile is None:
        profile = generate_financial_profile(txns, info, meta, issues)

    annotated_txns = profile.get("annotated_transactions", txns)

    wb = Workbook()

    # 1. Financial Profile (Executive CAM Dashboard & Scorecard)
    ws_prof = wb.active
    ws_prof.title = "Financial_Profile"
    _write_financial_profile(ws_prof, profile)

    # 2. Income Analysis (Eligible Income & Exclusions)
    ws_inc = wb.create_sheet("Income_Analysis")
    _write_income_analysis(ws_inc, profile)

    # 3. Monthly Analysis (with Underwriting Ratios)
    ws_month = wb.create_sheet("Monthly_Analysis")
    _write_monthly_analysis(ws_month, profile)

    # 4. Transactions (Full Ledger with Classification)
    ws_txns = wb.create_sheet("Transactions")
    _write_transactions(ws_txns, annotated_txns, issues)

    # 5. Customer Info
    ws_info = wb.create_sheet("Customer_Info")
    _write_customer_info(ws_info, annotated_txns, info, meta, profile.get("executive_summary"))

    # 6. Debt Obligations (FOIR & DSCR)
    ws_debt = wb.create_sheet("Debt_Obligations")
    _write_debt_obligations(ws_debt, profile)

    # 7. Counterparties & Channels
    ws_cp = wb.create_sheet("Counterparties")
    _write_counterparties(ws_cp, profile)

    # 8. Risk & Anomaly Flags (AML with Confidence)
    ws_risk = wb.create_sheet("Risk_Anomaly_Flags")
    _write_risk_flags(ws_risk, profile)

    # 9. Validation Audit
    ws_val = wb.create_sheet("Validation")
    _write_validation(ws_val, annotated_txns, issues, meta)

    # 10. PDF Field Validation
    ws_fval = wb.create_sheet("PDF_Field_Validation")
    _write_pdf_field_validation(ws_fval, annotated_txns)

    # 11. Calculation Reconciliation
    ws_recon = wb.create_sheet("Calculation_Reconciliation")
    _write_calculation_reconciliation(ws_recon, profile, meta, annotated_txns)

    wb.save(path)
    return path


# --------------------------------------------------------------------------
# Sheet Builders
# --------------------------------------------------------------------------

def _write_financial_profile(ws, profile: dict):
    exec_s = profile.get("executive_summary", {})
    health = profile.get("account_health", {})
    debt = profile.get("debt_analysis", {})
    risk = profile.get("risk_analysis", {})
    scorecard = exec_s.get("scorecard_breakdown", {})

    ws.append(["EXECUTIVE FINANCIAL PROFILE & CREDIT APPRAISAL MEMORANDUM (CAM)", ""])
    ws.merge_cells("A1:B1")
    ws.cell(row=1, column=1).fill = HDR_FILL
    ws.cell(row=1, column=1).font = Font(name="Arial", size=12, bold=True, color="FFFFFF")

    ws.append(["", ""])
    ws.append(["1. Customer & Facility Profile", ""])
    ws.cell(row=3, column=1).fill = SEC_FILL
    ws.cell(row=3, column=1).font = SEC_FONT
    ws.merge_cells("A3:B3")

    for k, v in [
        ("Account Holder", exec_s.get("account_holder")),
        ("Bank Name", exec_s.get("bank_name")),
        ("Account Number", exec_s.get("account_number")),
        ("Banking Facility Type", exec_s.get("facility_type")),
        *_account_type_rows(exec_s),
        ("Unclassified Share of Flows", f"{exec_s.get('unclassified_flow_share_pct', 0):.1f}%"),
        ("Components Not Scored (total rescaled)", ", ".join(exec_s.get("unscored_components") or []) or "None"),
        ("Customer Persona", exec_s.get("customer_persona")),
        ("Statement Completeness", exec_s.get("statement_completeness")),
    ]:
        ws.append([k, str(v) if v is not None else "N/A"])

    ws.append(["", ""])
    ws.append(["2. Credit Appraisal & Underwriting Scorecard", ""])
    r_sc = ws.max_row
    ws.cell(row=r_sc, column=1).fill = SEC_FILL
    ws.cell(row=r_sc, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r_sc}:B{r_sc}")

    score_val = exec_s.get("credit_score_index", 0.0)
    rating_val = exec_s.get("risk_rating", "N/A")

    dscr_display = exec_s.get("dscr_display")
    if not dscr_display:
        dscr_display = (
            f"{exec_s.get('dscr'):.2f}x ({exec_s.get('dscr_assessment', '')})"
            if exec_s.get("dscr") is not None
            else (
                "N/A — No Debt Service (Debt Burden: 0%)"
                if exec_s.get("total_monthly_debt_service", 0) == 0
                else "N/A (Individual / Retail Account)"
            )
        )

    inc_label = exec_s.get("income_metric_label", "Monthly Eligible Income")
    debt_ratio_label = exec_s.get("debt_ratio_label", "FOIR (Debt-to-Income)")
    cov_ratio = exec_s.get("operating_cash_coverage_ratio")
    cov_status = exec_s.get("operating_cash_coverage_status", "N/A")
    cov_display = f"{cov_ratio:.2f}x ({cov_status})" if cov_ratio is not None else cov_status

    score_val = exec_s.get("credit_score_index", 0.0)
    rating_val = exec_s.get("risk_rating", "N/A")
    data_suff = exec_s.get("data_sufficiency", exec_s.get("analysis_sample_confidence", "N/A"))
    analysis_per = exec_s.get("analysis_period", f"{exec_s.get('months_count', 1)} Month(s) Audited")

    uw_baseline = exec_s.get("underwriting_income_baseline", exec_s.get("monthly_eligible_income", 0.0))

    card_rows = [
        ("Overall Credit Score Index (0-100)", f"{score_val:.1f} / 100"),
        ("Underwriting Risk Grade", rating_val),
        ("Analysis Period", analysis_per),
        ("Period Basis", exec_s.get("analysis_period_basis", "-")),
        ("Statement Coverage", f"{exec_s.get('statement_coverage_start') or '-'} to "
                               f"{exec_s.get('statement_coverage_end') or '-'} "
                               f"(from {exec_s.get('statement_coverage_source', '-')})"),
        ("Transaction Period", f"{exec_s.get('transaction_period_start') or '-'} to "
                               f"{exec_s.get('transaction_period_end') or '-'} (first to last actual transaction)"),
        ("Data Sufficiency", data_suff),
        ("Eligible Monthly Income (used in every ratio)", f"₹ {uw_baseline:,.2f}"),
        ("Average Bank Balance (ABB)", f"₹ {exec_s.get('abb', 0):,.2f}"),
        ("Eligible Operating Receipts Identified", f"₹ {exec_s.get('true_operating_revenue', 0):,.2f}"),
        ("Gross Bank Inflows", f"₹ {exec_s.get('gross_bank_inflows', 0):,.2f}"),
        ("Non-Operating Inflows (Excluded)", f"₹ {exec_s.get('total_excluded_inflows', 0):,.2f}"),
    ]

    if exec_s.get("total_cash_deposits", 0) > 0:
        card_rows.extend([
            ("Total Cash Deposits", f"₹ {exec_s.get('total_cash_deposits', 0):,.2f}"
             f" ({exec_s.get('cash_share_of_inflows_pct', 0):.1f}% of inflows)"),
            ("  Verified Business Receipts (identified payers, non-cash)",
             f"₹ {exec_s.get('verified_business_receipts', 0):,.2f}"),
            ("  Unverified Cash Deposits (not counted as income)",
             f"₹ {exec_s.get('unverified_cash_deposits', 0):,.2f}"),
        ])
        if exec_s.get("cash_funded_payments"):
            card_rows.append(("  Payments Funded by that Cash (set aside with it)",
                              f"₹ {exec_s['cash_funded_payments']:,.2f}"))

    if profile.get("eligible_income", {}).get("median_monthly_salary"):
        card_rows.append(("  of which: Median Monthly Salary (information only)",
                          f"₹ {profile['eligible_income']['median_monthly_salary']:,.2f}"))

    card_rows.extend([
        ("Monthly Operating Expenses (Excl. Debt/Taxes)", f"₹ {exec_s.get('monthly_operating_expenses', 0):,.2f}"),
        ("Operating Cash Available (before Debt)", f"₹ {exec_s.get('monthly_operating_cash_available', 0):,.2f}"),
        ("EMIs Actually Paid (per month, in debt service)", f"₹ {exec_s.get('monthly_emi_paid', 0):,.2f}"),
        ("Current EMI on Active Loans (forward-looking)", f"₹ {exec_s.get('total_monthly_emi', 0):,.2f}"),
        ("Total Monthly Debt Service (EMIs paid + Interest)", f"₹ {exec_s.get('total_monthly_debt_service', 0):,.2f}"),
        ("Estimated Monthly Operating Surplus", f"₹ {exec_s.get('estimated_monthly_operating_surplus', 0):,.2f}"),
        ("Operating Margin", f"{exec_s['operating_margin_pct']:.1f}%" if exec_s.get("operating_margin_pct") is not None
         else f"N/M — {exec_s.get('operating_margin_nm_reason') or 'not meaningful'}"),
        (debt_ratio_label, f"{exec_s['foir_percentage']:.2f}% ({debt.get('foir_risk_category', '')})"
         if exec_s.get('foir_percentage') is not None else "N/M (no meaningful eligible income)"),
        ("Debt Service Coverage Ratio (DSCR)", dscr_display),
    ])
    if exec_s.get("dscr_incl_unverified_cash") is not None:
        card_rows.append(("  DSCR if Unverified Cash Were Income (not scored)",
                          f"{exec_s['dscr_incl_unverified_cash']:.2f}x"))

    raw_dscr = exec_s.get("raw_dscr")
    if raw_dscr is not None and (exec_s.get("dscr") is None or raw_dscr < 0):
        card_rows.append(("DSCR Reason", "Negative operating cash flow"))
        card_rows.append(("Raw Operating Cash / Debt Service", f"{raw_dscr:.2f}x"))

    card_rows.append(("Operating Cash Coverage", cov_display))
    card_rows.append(("Active Loans Detected", exec_s.get("active_loans_count", 0)))

    if health.get("is_overdraft_facility"):
        card_rows.extend([
            ("Sanctioned OD Limit (Printed)", _fmt_or_na(exec_s.get('estimated_sanctioned_limit'), "₹ {:,.2f}")),
            ("Average OD Limit Utilization", _fmt_or_na(exec_s.get('average_limit_utilization_pct'), "{:.1f}%")),
            ("Credit Turnover-to-Limit Multiplier", _fmt_or_na(exec_s.get('credit_turnover_to_limit'), "{:.1f}x (Norm: 4-6x)")),
            ("Peak Overdraft Drawn", f"₹ {abs(risk.get('peak_negative_overdraft', 0)):,.2f}"),
        ])
    else:
        card_rows.extend([
            ("Negative Balance Days", health.get("negative_balance_days", 0)),
            ("Peak Overdraft Utilized", f"₹ {abs(risk.get('peak_negative_overdraft', 0)):,.2f}"),
        ])

    card_rows.append(("Loan EMI Repayment Regularity", exec_s.get("loan_emi_regularity", "REGULAR — 0 EMI Bounces")))
    card_rows.append(("Overall Banking Payment Behavior", f"{exec_s.get('outward_bounces', 0)} Outward / ECS Bounces"))

    for k, v in card_rows:
        ws.append([k, v])

    # Hard-capping rules section
    hard_caps = exec_s.get("hard_cap_rules_applied", [])
    if hard_caps:
        ws.append(["", ""])
        ws.append(["Hard Capping Rules Enforced by Engine", ""])
        r_hc = ws.max_row
        ws.cell(row=r_hc, column=1).fill = BAD
        ws.cell(row=r_hc, column=1).font = Font(name="Arial", size=10, bold=True, color="9C0006")
        ws.merge_cells(f"A{r_hc}:B{r_hc}")
        for hc in hard_caps:
            ws.append(["🛑", hc])

    # 8-Component Scorecard Breakdown Table
    ws.append(["", ""])
    ws.append(["3. 8-Component Underwriting Scorecard Breakdown (100 Points)", ""])
    r_sc_tbl = ws.max_row
    ws.cell(row=r_sc_tbl, column=1).fill = SEC_FILL
    ws.cell(row=r_sc_tbl, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r_sc_tbl}:B{r_sc_tbl}")

    ws.append(["Scoring Dimension", "Points Awarded / Max Points"])
    r_hdr_sc = ws.max_row
    ws.cell(row=r_hdr_sc, column=1).fill = SUB_HDR_FILL
    ws.cell(row=r_hdr_sc, column=1).font = SUB_HDR_FONT
    ws.cell(row=r_hdr_sc, column=2).fill = SUB_HDR_FILL
    ws.cell(row=r_hdr_sc, column=2).font = SUB_HDR_FONT

    is_salaried = profile.get("income", {}).get("is_salaried", False) or "Salaried" in exec_s.get("customer_persona", "")
    if is_salaried:
        debt_cap_label = "Debt Repayment Capacity / Obligation Burden (FOIR & Debt Burden)"
    elif exec_s.get("customer_persona") == "Commercial / Business Entity" or health.get("facility_type") in ("CURRENT", "OVERDRAFT_CC"):
        debt_cap_label = "Debt Repayment Capacity (DSCR & Debt-to-Revenue)"
    else:
        debt_cap_label = "Debt Repayment Capacity / Obligation Burden"

    reasons = exec_s.get("unscored_reasons", {})
    for k, v, key, max_pts in [
        ("Cash-Flow Stability & Margin", scorecard.get("cashflow_margin_score", 0), "cashflow_margin_score", 20),
        ("Liquidity & ABB Cushion", scorecard.get("liquidity_abb_score", 0), "liquidity_abb_score", 15),
        (debt_cap_label, scorecard.get("debt_capacity_score", 0), "debt_capacity_score", 15),
        ("EMI Repayment Regularity", scorecard.get("emi_regularity_score", 0), "emi_regularity_score", 10),
        ("Facility Compliance & OD Utilization", scorecard.get("facility_compliance_score", 0), "facility_compliance_score", 15),
        ("Bounce & Return Behavior", scorecard.get("bounce_behavior_score", 0), "bounce_behavior_score", 10),
        ("Transaction Risk & AML Structuring", scorecard.get("transaction_risk_score", 0), "transaction_risk_score", 10),
        ("Income Stability & Concentration", scorecard.get("income_concentration_score", 0), "income_concentration_score", 5),
    ]:
        # a component the statement cannot support is left out, and the total rescaled
        ws.append([k, f"{v:.1f} / {max_pts} pts" if v is not None
                   else f"Not scored ({reasons.get(key, 'not measurable from this statement')})"])

    ws.append(["", ""])
    ws.append(["4. Key Underwriting Strengths", ""])
    row_str = ws.max_row
    ws.cell(row=row_str, column=1).fill = GOOD
    ws.cell(row=row_str, column=1).font = Font(name="Arial", size=10, bold=True, color="276A3C")
    ws.merge_cells(f"A{row_str}:B{row_str}")

    for s in exec_s.get("strengths", ["Standard banking profile"]):
        ws.append(["✓", s])

    ws.append(["", ""])
    ws.append(["5. Underwriting Red Flags & Concerns", ""])
    row_rf = ws.max_row
    ws.cell(row=row_rf, column=1).fill = BAD
    ws.cell(row=row_rf, column=1).font = Font(name="Arial", size=10, bold=True, color="9C0006")
    ws.merge_cells(f"A{row_rf}:B{row_rf}")

    for rf in exec_s.get("red_flags", ["No major red flags detected"]):
        ws.append(["⚠", rf])

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 54

    for r in range(1, ws.max_row + 1):
        c1 = ws.cell(row=r, column=1)
        c2 = ws.cell(row=r, column=2)
        if c1.value and not c1.fill.fill_type:
            c1.font = BODY_BOLD
            c2.font = BODY
            c1.border = THIN
            c2.border = THIN
        if c1.value == "Underwriting Risk Grade":
            if "PRIME" in str(c2.value) or "LOW RISK" in str(c2.value):
                c2.fill = GOOD
                c2.font = BODY_BOLD
            elif "STRESSED" in str(c2.value) or "HIGH RISK" in str(c2.value):
                c2.fill = BAD
                c2.font = BODY_BOLD
            else:
                c2.fill = WARN
        if c1.value in ("Data Sufficiency", "Analysis Sample Confidence"):
            if "STRONG" in str(c2.value):
                c2.fill = GOOD
                c2.font = BODY_BOLD
            elif "VERY LIMITED" in str(c2.value):
                c2.fill = BAD
                c2.font = BODY_BOLD
            elif "LIMITED" in str(c2.value):
                c2.fill = WARN
                c2.font = BODY_BOLD
            else:
                c2.font = BODY_BOLD


def _write_income_analysis(ws, profile: dict):
    el_inc = profile.get("eligible_income", {})

    ws.append(["ELIGIBLE INCOME & INFLOW UNDERWRITING AUDIT", "", "", ""])
    ws.merge_cells("A1:D1")
    ws.cell(row=1, column=1).fill = HDR_FILL
    ws.cell(row=1, column=1).font = Font(name="Arial", size=12, bold=True, color="FFFFFF")

    ws.append(["", "", "", ""])
    ws.append(["Metric", "Amount", "", ""])
    r_hdr = ws.max_row
    ws.cell(row=r_hdr, column=1).fill = SEC_FILL
    ws.cell(row=r_hdr, column=1).font = SEC_FONT
    ws.cell(row=r_hdr, column=2).fill = SEC_FILL
    ws.cell(row=r_hdr, column=2).font = SEC_FONT

    inc_label = el_inc.get("income_metric_label", "Monthly Eligible Income")
    uw_baseline = el_inc.get("underwriting_income_baseline", el_inc.get("monthly_eligible_income", 0.0))
    baseline_type = el_inc.get("underwriting_baseline_type", "100% of Verified Inflows Run-Rate")
    data_suff = profile.get("executive_summary", {}).get("data_sufficiency", "N/A")
    analysis_per = profile.get("executive_summary", {}).get("analysis_period", f"{el_inc.get('months_count', 1)} Month(s) Audited")

    metrics_list = [
        ("Eligible Monthly Income (used in every ratio)", f"₹ {uw_baseline:,.2f}"),
        ("Definition", baseline_type),
        ("Median Monthly Salary (information only, not used in ratios)",
         f"₹ {el_inc.get('median_monthly_salary', 0):,.2f}" if el_inc.get("median_monthly_salary") else "No salary credits"),
        ("Eligible Operating Receipts Identified in Period", f"₹ {el_inc.get('total_eligible_income', 0):,.2f}"),
        ("Analysis Period", analysis_per),
        ("Period Basis", profile.get("executive_summary", {}).get("analysis_period_basis", "-")),
        ("Statement Coverage", "{} to {} (from {})".format(
            profile.get("executive_summary", {}).get("statement_coverage_start") or "-",
            profile.get("executive_summary", {}).get("statement_coverage_end") or "-",
            profile.get("executive_summary", {}).get("statement_coverage_source", "-"))),
        ("Transaction Period", "{} to {} (first to last actual transaction)".format(
            profile.get("executive_summary", {}).get("transaction_period_start") or "-",
            profile.get("executive_summary", {}).get("transaction_period_end") or "-")),
        ("Data Sufficiency", data_suff),
        ("Total Excluded Inflows (Non-Operating)", f"₹ {el_inc.get('total_excluded_inflows', 0):,.2f}"),
    ]
    if el_inc.get("total_cash_deposits", 0) > 0:
        metrics_list.extend([
            ("Total Cash Deposits", f"₹ {el_inc.get('total_cash_deposits', 0):,.2f}"
             f" ({el_inc.get('cash_share_of_inflows_pct', 0):.1f}% of inflows)"),
            ("  Verified Business Receipts (identified payers, non-cash)",
             f"₹ {el_inc.get('verified_business_receipts', 0):,.2f}"),
            ("  Unverified Cash Deposits (not counted as income)",
             f"₹ {el_inc.get('unverified_cash_deposits', 0):,.2f}"),
            ("  Payments Funded by that Cash (not counted as expenses)",
             f"₹ {el_inc.get('cash_funded_payments', 0):,.2f} ({el_inc.get('cash_funded_payments_count', 0)} payments)"),
            ("Cash Source Note", "A statement shows cash came in, not where from; verify with sales records / GST before counting it"),
        ])

    metrics_list.extend([
        ("Gross Bank Inflows (Total Credits)", f"₹ {el_inc.get('gross_credits', 0):,.2f}"),
        ("Monthly Operating Expenses (Excl. Debt/Taxes)", f"₹ {el_inc.get('monthly_operating_expenses', 0):,.2f}"),
        ("Total Operating Expenses in Period", f"₹ {el_inc.get('total_operating_expenses', 0):,.2f}"),
        ("Total Excluded Debits (Transfers, Taxes, Debt)", f"₹ {el_inc.get('total_excluded_debits', 0):,.2f}"),
        ("Gross Bank Outflows (Total Debits)", f"₹ {el_inc.get('gross_debits', 0):,.2f}"),
        ("Monthly Debt Service (EMI + Interest)", f"₹ {el_inc.get('monthly_debt_service', 0):,.2f}"),
        ("Estimated Monthly Operating Surplus", f"₹ {el_inc.get('estimated_operating_surplus', 0):,.2f}"),
        ("Months Audited (days covered / 30.4)", el_inc.get("months_count", 1)),
        ("Calendar Months with Activity", el_inc.get("calendar_months_with_activity", "-")),
        ("Unclassified Inflows (not counted as income)",
         f"₹ {el_inc.get('total_unclassified_inflows', 0):,.2f} ({el_inc.get('unclassified_inflow_share_pct', 0):.1f}% of credits)"),
        ("Top Payer Share of Eligible Operating Receipts",
         f"{el_inc.get('concentration', {}).get('top1_share_pct', 0):.1f}% ({el_inc.get('concentration', {}).get('top1_payer', '-')})"
         if el_inc.get("income_meaningful", True) else "N/M (no meaningful eligible income)"),
    ])

    for k, v in metrics_list:
        ws.append([k, v, "", ""])

    ws.append(["", "", "", ""])
    ws.append(["1. Eligible Inflow Categories (Operating Revenue)", "", "", ""])
    r1 = ws.max_row
    ws.cell(row=r1, column=1).fill = SEC_FILL
    ws.cell(row=r1, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r1}:D{r1}")

    ws.append(["Inflow Category", "Txn Count", "Total Amount", "Monthly Run-Rate"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    m_count = max(0.1, el_inc.get("months_count", 1) or 1)
    for cat in el_inc.get("eligible_categories", []):
        m_rate = cat["amount"] / m_count
        ws.append([cat["category"], cat["count"], cat["amount"], m_rate])

    ws.append(["", "", "", ""])
    ws.append(["2. Excluded Inflows & Funding Channels (Non-Operating)", "", "", ""])
    r2 = ws.max_row
    ws.cell(row=r2, column=1).fill = SEC_FILL
    ws.cell(row=r2, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r2}:D{r2}")

    ws.append(["Excluded Category", "Txn Count", "Total Amount", "Reason for Underwriting Exclusion"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    for ex in el_inc.get("excluded_categories", []):
        ws.append([ex["category"], ex["count"], ex["amount"], ex["reason"]])

    # Section 3: Operating Expense Deductions / Excluded Debits
    debit_reasons = {
        "Self / Contra Transfers (DR)": "Internal transfers between borrower's own accounts or related entities",
        "Direct / Indirect Taxes (GST / IT)": "Statutory tax liabilities (GST, Advance Tax, TDS)",
        "Financing & OD Interest": "Interest expense on borrowings and overdrafts (analyzed under Debt Service)",
        "Loan EMI Repayments": "Debt principal and installment obligations (analyzed under Debt Service)",
        "Investments & Sweeps": "Capital allocations to FDs, mutual funds, securities, or sweep-outs",
        "Credit Card Bill Repayments": "Repayment of credit card liabilities",
        "Cheque / ECS Bounce Charges": "Bank penal charges for returned payments",
        "Loan Outflow Reversals": "Reversed or pass-through loan transactions",
    }
    excluded_debits = el_inc.get("excluded_debit_categories", [])
    if excluded_debits:
        ws.append(["", "", "", ""])
        ws.append(["3. Operating Expense Deductions & Excluded Debits", "", "", ""])
        r3 = ws.max_row
        ws.cell(row=r3, column=1).fill = SEC_FILL
        ws.cell(row=r3, column=1).font = SEC_FONT
        ws.merge_cells(f"A{r3}:D{r3}")

        ws.append(["Non-Operating Debit Category", "Txn Count", "Total Amount", "Underwriting Rationale"])
        _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

        for ed in excluded_debits:
            rationale = debit_reasons.get(ed["category"], "Non-operating financing or statutory debit")
            ws.append([ed["category"], ed["count"], ed["amount"], rationale])

    col_widths = [42, 12, 18, 55]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    for r in range(2, ws.max_row + 1):
        c1 = ws.cell(row=r, column=1)
        if c1.value and not c1.fill.fill_type:
            for c in range(1, 5):
                ws.cell(row=r, column=c).font = BODY
                ws.cell(row=r, column=c).border = THIN
            ws.cell(row=r, column=3).number_format = '#,##0.00;[Red]-#,##0.00'


def _write_monthly_analysis(ws, profile: dict):
    headers = [
        "Month", "Inflow (Cr)", "Outflow (Dr)", "Net Cash Flow", "Closing Bal",
        "ABB / AMB", "Net Cash Margin", "Outflow Ratio", "Cash Wdl Ratio", "Gross Net Flow Status",
        "Eligible Receipts", "Operating Exp + Debt Service", "Operating Net", "Operating Status",
    ]
    ws.append(headers)
    _style_header(ws, row=1)

    cashflow_m = {x["month"]: x for x in profile.get("cash_flow", {}).get("monthly_summary", [])}
    health_m = {x["month"]: x for x in profile.get("account_health", {}).get("monthly_health", [])}
    exp_m = {x["month"]: x for x in profile.get("expense_analysis", {}).get("monthly_breakdown", [])}
    op_m = {x["month"]: x for x in profile.get("eligible_income", {}).get("monthly_operating", [])}

    all_months = sorted(set(cashflow_m.keys()) | set(health_m.keys()))
    # a ratio to a month's inflow means nothing when that month barely had any
    # (Cosmos Thane 2020-05: -1180%); 'barely' is relative to this account
    inflows = sorted(x.get("inflow", 0.0) for x in cashflow_m.values() if x.get("inflow", 0.0) > 0)
    typical_inflow = inflows[len(inflows) // 2] if inflows else 0.0

    for m in all_months:
        cf = cashflow_m.get(m, {})
        hl = health_m.get(m, {})
        ex = exp_m.get(m, {})
        inf = cf.get("inflow", 0.0)
        outf = cf.get("outflow", 0.0)
        net = cf.get("net_flow", 0.0)
        cash_wdl = ex.get("cash_withdrawals", 0.0)

        # 5 Financial Underwriting Ratios
        meaningful = inf > 0 and inf >= 0.1 * typical_inflow
        margin = (net / inf) if meaningful else "N/M"
        outflow_ratio = (outf / inf) if meaningful else "N/M"
        cash_ratio = (cash_wdl / outf) if outf > 0 else 0.0

        ws.append([
            m,
            inf,
            outf,
            net,
            hl.get("closing_balance", 0.0),
            hl.get("abb", 0.0),
            margin,
            outflow_ratio,
            cash_ratio,
            cf.get("status", "NO ACTIVITY" if (inf == 0 and outf == 0) else ("SURPLUS" if net > 0 else "DEFICIT")),
            op_m.get(m, {}).get("eligible_receipts", 0.0),
            op_m.get(m, {}).get("operating_expenses", 0.0) + op_m.get(m, {}).get("debt_service", 0.0),
            op_m.get(m, {}).get("operating_net", 0.0),
            op_m.get(m, {}).get("operating_status", "-"),
        ])

    col_widths = [14, 18, 18, 18, 18, 16, 16, 14, 16, 20, 18, 22, 18, 16]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    for r in range(2, ws.max_row + 1):
        for c in range(1, len(col_widths) + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY
            cell.border = THIN
            if c in (2, 3, 4, 5, 6, 11, 12, 13):
                cell.number_format = '#,##0.00;[Red]-#,##0.00'
            elif c in (7, 8, 9):
                cell.number_format = '0.0%'
        for col in (10, 14):
            stat_cell = ws.cell(row=r, column=col)
            stat_cell.alignment = Alignment(horizontal="center")
            if stat_cell.value == "DEFICIT":
                stat_cell.fill = WARN
            elif stat_cell.value in ("SURPLUS", "NO ACTIVITY"):
                stat_cell.fill = GOOD


def _write_transactions(ws, txns, issues):
    ws.append([c[0] for c in TXN_COLS])
    flagged = {i for i, _ in issues}

    for n, t in enumerate(txns, 1):
        typ = "DR" if t.get("debit") else ("CR" if t.get("credit") else "")
        ref_val = str(t["reference"]) if t.get("reference") is not None else ""
        cat_val = t.get("category") or "GENERAL_TRANSFER"
        cp_val = t.get("counterparty") or "Unknown"

        ws.append([
            n, t.get("txn_date"), t.get("value_date"), t.get("narration"), ref_val,
            _f(t.get("debit")), _f(t.get("credit")), _f(t.get("balance")), typ,
            cat_val, cp_val, t.get("counterparty_id") or "", t.get("relationship") or "",
            t.get("purpose") or "-", t.get("page", 1),
            "CHECK" if (n - 1) in flagged else "OK"
        ])

    for i, (name, w) in enumerate(TXN_COLS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.column_dimensions[get_column_letter(5)].number_format = "@"

    for r in range(2, ws.max_row + 1):
        for c in range(1, len(TXN_COLS) + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY
            cell.border = THIN
        for c in (2, 3):
            ws.cell(row=r, column=c).number_format = "dd-mm-yyyy"
        ref_cell = ws.cell(row=r, column=5)
        ref_cell.number_format = "@"
        ref_cell.data_type = "s"
        if ref_cell.value:
            ref_cell.quotePrefix = True
        for c in (6, 7, 8):
            ws.cell(row=r, column=c).number_format = '#,##0.00;[Red]-#,##0.00'

        narr = ws.cell(row=r, column=4).value or ""
        ws.cell(row=r, column=4).alignment = Alignment(wrap_text=True, vertical="top")
        nlines = max(1, (len(str(narr)) + 69) // 70)
        ws.row_dimensions[r].height = 15 * min(nlines, 6)

        # Subtle Category Highlighting
        cat_cell = ws.cell(row=r, column=10)
        if cat_cell.value == "LOAN_EMI":
            cat_cell.font = BODY_BOLD
            cat_cell.fill = PatternFill("solid", fgColor="F2E6FF")
        elif cat_cell.value in ("SALARY", "BUSINESS_RECEIPT"):
            cat_cell.font = BODY_BOLD
            cat_cell.fill = PatternFill("solid", fgColor="E8F8F0")
        elif cat_cell.value in ("BOUNCE_PENALTY", "BANK_CHARGES"):
            cat_cell.font = BODY_BOLD
            cat_cell.fill = PatternFill("solid", fgColor="FFEAEA")
        elif cat_cell.value in ("CASH_WITHDRAWAL", "CASH_DEPOSIT"):
            cat_cell.fill = PatternFill("solid", fgColor="FFF8E7")

        if ws.cell(row=r, column=len(TXN_COLS)).value == "CHECK":
            for c in range(1, len(TXN_COLS) + 1):
                ws.cell(row=r, column=c).fill = WARN

    _style_header(ws)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(TXN_COLS))}{ws.max_row}"


def _account_type_rows(e: dict) -> list[tuple]:
    """Resolved account and borrower type, with where each answer came from."""
    if not e or not e.get("account_type"):
        return []
    return [
        ("Account Type (resolved)", e["account_type"] + (f" / {e['account_subtype']}" if e.get("account_subtype") else "")),
        ("Account Type (printed text)", e.get("account_type_raw") or "not printed"),
        ("Account Type Resolved At", f"step {e.get('account_type_step')} — confidence {e.get('account_type_confidence')}"),
        ("Account Type Evidence", e.get("account_type_evidence") or "-"),
        ("Account Type Conflicts", "; ".join(e.get("account_type_conflicts") or []) or "None"),
        ("Borrower Type", f"{e.get('borrower_type')} — confidence {e.get('borrower_type_confidence')}"),
        ("Borrower Type Evidence", e.get("borrower_type_evidence") or "-"),
    ]


def _write_customer_info(ws, txns, info, meta, exec_s=None):
    ws.append(["Field", "Value"])
    order = [
        "bank", "customer_name", "account_number", "account_type", "customer_id",
        "ifsc", "micr", "branch", "address", "email", "phone", "pan", "currency",
        "period_from", "period_to", "opening_balance_printed"
    ]
    text_fields = {"account_number", "customer_id", "micr", "ifsc", "pan", "phone"}
    seen = set()

    for k in order + [k for k in info if k not in order]:
        if k in seen or k not in info:
            continue
        seen.add(k)
        val = str(info[k]) if k in text_fields and info[k] is not None else info[k]
        if k == "linked_accounts":
            # accounts from earlier statements whose holder shares contact details
            val = "; ".join(f"{x['account_number']} {x.get('customer_name', '')} ({x.get('bank', '')}) "
                            f"— shares {', '.join(x['shared'])}" for x in val) or "None found"
        if k == "account_type" and (exec_s or {}).get("account_type"):
            continue                    # shown below as 'Account Type (printed text)'
        label = "Account Type (printed)" if k == "account_type" else k.replace("_", " ").title()
        ws.append([label, val])
    for label, val in _account_type_rows(exec_s or {}):
        ws.append([label, val])

    ws.append(["", ""])
    dated_count = sum(1 for t in txns if t.get("txn_date") is not None)
    date_completeness = f"{(dated_count / max(1, len(txns))) * 100:.2f}%"
    narr_count = sum(1 for t in txns if (t.get("narration") or "").strip())
    narration_completeness = f"{(narr_count / max(1, len(txns))) * 100:.2f}%"

    field_records, field_summary = validate_field_linkage(txns)

    for k, v in [
        ("Transaction Count", len(txns)),
        ("Total Debit", _f(sum((t.get("debit") or Decimal(0)) for t in txns))),
        ("Total Credit", _f(sum((t.get("credit") or Decimal(0)) for t in txns))),
        ("Opening Balance (derived)", _f(meta.get("opening"))),
        ("Closing Balance (derived)", _f(meta.get("closing"))),
        ("Date Field Completeness", date_completeness),
        ("Narration Field Completeness", narration_completeness),
        ("PDF Field Linkage Pass Rate", f"{field_summary['overall_accuracy'] * 100:.2f}%"),
        ("Statement Completeness", meta.get("completeness", "COMPLETE")),
        ("Column Headers", meta.get("column_headers", "matched exactly")),
    ]:
        ws.append([k, v])

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 62
    ws.column_dimensions["B"].number_format = "@"

    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=1).font = Font(name="Arial", size=10, bold=True)
        c2 = ws.cell(row=r, column=2)
        c2.font = BODY
        if isinstance(c2.value, str):
            c2.number_format = "@"
            c2.quotePrefix = True
        if ws.cell(row=r, column=1).value in ("Date Field Completeness", "Narration Field Completeness", "PDF Field Linkage Pass Rate") and c2.value != "100.00%":
            c2.fill = WARN
        if ws.cell(row=r, column=1).value == "Statement Completeness" and str(c2.value or "").startswith("PARTIAL"):
            c2.fill = WARN

    _style_header(ws)


def _write_debt_obligations(ws, profile: dict):
    debt = profile.get("debt_analysis", {})

    ws.append(["DEBT & LOAN OBLIGATIONS (FOIR / REPAYMENT AUDIT)", ""])
    ws.merge_cells("A1:E1")
    ws.cell(row=1, column=1).fill = HDR_FILL
    ws.cell(row=1, column=1).font = Font(name="Arial", size=11, bold=True, color="FFFFFF")

    ws.append(["", "", "", "", ""])
    ws.append(["Metric", "Value", "", "", ""])
    row_hdr = ws.max_row
    ws.cell(row=row_hdr, column=1).fill = SEC_FILL
    ws.cell(row=row_hdr, column=1).font = SEC_FONT
    ws.cell(row=row_hdr, column=2).fill = SEC_FILL
    ws.cell(row=row_hdr, column=2).font = SEC_FONT

    dscr_val = debt.get("dscr_display")
    if not dscr_val:
        dscr_val = (
            f"{debt.get('dscr'):.2f}x ({debt.get('dscr_assessment', '')})"
            if debt.get('dscr') is not None
            else (
                "N/A — No Debt Service (Debt Burden: 0%)"
                if debt.get('total_monthly_debt_service', 0) == 0
                else "N/A (Retail)"
            )
        )

    cov_ratio = debt.get("operating_cash_coverage_ratio")
    cov_status = debt.get("operating_cash_coverage_status", "N/A")
    cov_display = f"{cov_ratio:.2f}x ({cov_status})" if cov_ratio is not None else cov_status
    debt_ratio_label = debt.get("debt_ratio_label", "FOIR (Debt-to-Income)")

    debt_rows = [
        ("Active Loan Accounts Detected", debt.get("active_loans_count", 0)),
        ("Loans Seen in Statement (incl. closed / not paid in last 45 days)", debt.get("loans_detected_count", 0)),
        ("EMIs Actually Paid (per month, in debt service)", f"₹ {debt.get('monthly_emi_paid', 0):,.2f}"),
        ("Current EMI on Active Loans (forward-looking)", f"₹ {debt.get('total_monthly_emi_obligation', 0):,.2f}"),
        ("Monthly Financing / OD Interest Obligation", f"₹ {debt.get('total_monthly_interest_obligation', 0):,.2f}"),
        ("Total Monthly Debt Service (EMIs paid + Interest)", f"₹ {debt.get('total_monthly_debt_service', 0):,.2f}"),
        ("Monthly Credit Card Repayments (in operating expenses)", f"₹ {debt.get('total_monthly_card_repayments', 0):,.2f}"),
        ("Operating Cash Available for Debt Service (CADS)", f"₹ {debt.get('monthly_operating_cash_available', 0):,.2f}"),
        ("Total Loan Repayments in Period", f"₹ {debt.get('total_emi_paid_in_period', 0):,.2f}"),
        ("Credit Card Bill Repayments", f"₹ {debt.get('credit_card_repayments_paid', 0):,.2f}"),
        ("Financing / OD Interest Serviced in Period", f"₹ {debt.get('interest_expenses_paid', 0):,.2f}"),
        (debt_ratio_label, f"{debt['foir_percentage']:.2f}% ({debt.get('foir_calculation_type', '')})"
         if debt.get('foir_percentage') is not None else "N/M (no meaningful eligible income)"),
        (f"{debt_ratio_label} Risk Category", debt.get("foir_risk_category", "N/A")),
        ("Debt Service Coverage Ratio (DSCR)", dscr_val),
    ]
    if debt.get("dscr_incl_unverified_cash") is not None:
        debt_rows.append(("  DSCR if Unverified Cash Were Income (not scored)",
                          f"{debt['dscr_incl_unverified_cash']:.2f}x"))

    raw_dscr = debt.get("raw_dscr")
    if raw_dscr is not None and (debt.get("dscr") is None or raw_dscr < 0):
        debt_rows.append(("DSCR Reason", "Negative operating cash flow"))
        debt_rows.append(("Raw Operating Cash / Debt Service", f"{raw_dscr:.2f}x"))

    debt_rows.extend([
        ("Operating Cash Coverage", cov_display),
        ("Debt Burden Percentage", f"{debt['debt_burden_percentage']:.2f}%"
         if debt.get('debt_burden_percentage') is not None else "N/M (no meaningful eligible income)"),
        ("Loan EMI Repayment Regularity", debt.get("emi_regularity", "REGULAR — 0 EMI Bounces")),
    ])

    for k, v in debt_rows:
        ws.append([k, v, "", "", ""])

    ws.append(["", "", "", "", ""])
    ws.append(["Lender / Financer", "Monthly EMI (paid per month)", "Installments", "Total Paid",
               "Last Paid Date", "Loan Ref / Mandate", "Status", "Linked Bounces"])
    tbl1_row = ws.max_row
    _style_header(ws, row=tbl1_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    loans = debt.get("loans", [])
    if loans:
        for ln in loans:
            ws.append([
                ln["lender"], ln["typical_emi_amount"], ln["installments_detected"],
                ln["total_paid"], ln["last_paid_date"], ln.get("loan_reference", "-"),
                ln.get("status", "-"), ln.get("linked_bounces", 0),
            ])
    else:
        ws.append(["No term loan repayments identified in this statement", "-", "-", "-", "-"])

    ws.append(["", "", "", "", ""])
    ws.append(["Loan Disbursals Detected (Fresh Inflows)", "", "", "", ""])
    tbl2_title = ws.max_row
    ws.cell(row=tbl2_title, column=1).fill = SEC_FILL
    ws.cell(row=tbl2_title, column=1).font = SEC_FONT
    ws.merge_cells(f"A{tbl2_title}:E{tbl2_title}")

    ws.append(["Disbursal Date", "Amount", "Source / Lender", "Narration", ""])
    tbl2_row = ws.max_row
    _style_header(ws, row=tbl2_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    disb = debt.get("disbursals", [])
    if disb:
        for d in disb:
            ws.append([d["date"], d["amount"], d["source"], d["narration"], ""])
    else:
        ws.append(["No loan disbursals detected in this period", "-", "-", "-", ""])

    # Recurring debits no rule explained: possible EMIs to lenders not in the dictionary
    ws.append(["", "", "", "", ""])
    ws.append(["Recurring Debits for Review (monthly, same amount, not matched to a lender)", "", "", "", ""])
    t3 = ws.max_row
    ws.cell(row=t3, column=1).fill = SEC_FILL
    ws.cell(row=t3, column=1).font = SEC_FONT
    ws.merge_cells(f"A{t3}:E{t3}")
    ws.append(["Counterparty", "Amount", "Occurrences", "First Date", ""])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)
    rec = debt.get("recurring_debits_for_review", [])
    if rec:
        for r in rec:
            ws.append([r["counterparty"], r["amount"], r["occurrences"], r["first_date"], ""])
    else:
        ws.append(["None found", "-", "-", "-", ""])

    # Parties sharing the holder's name: neither own money nor arm's-length trade
    related = profile.get("counterparties", {}).get("possible_related_parties", [])
    ws.append(["", "", "", "", ""])
    ws.append(["Possible Related Parties (one line per counterparty, all of its transactions)", "", "", "", ""])
    t4 = ws.max_row
    ws.cell(row=t4, column=1).fill = SEC_FILL
    ws.cell(row=t4, column=1).font = SEC_FONT
    ws.merge_cells(f"A{t4}:E{t4}")
    ws.append(["Counterparty", "Inflow", "Outflow", "Transactions", "Purposes (each row keeps its own) / Basis"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)
    if related:
        for r in related:
            purposes = "; ".join(f"{p['purpose']}: ₹{p['amount']:,.0f}" for p in r.get("purposes", []))
            ws.append([r["counterparty"], r["inflow"], r["outflow"], r["count"],
                       f"{purposes} | related because: {r.get('relationship_basis', '-')}"])
    else:
        ws.append(["None found", "-", "-", "-", ""])

    col_widths = [35, 18, 14, 20, 16]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    for r in range(tbl1_row + 1, tbl1_row + 1 + max(1, len(loans))):
        for c in (2, 4):
            ws.cell(row=r, column=c).number_format = '#,##0.00;[Red]-#,##0.00'
        for c in range(1, 6):
            ws.cell(row=r, column=c).font = BODY
            ws.cell(row=r, column=c).border = THIN


def _write_counterparties(ws, profile: dict):
    cp_data = profile.get("counterparties", {})
    channels = profile.get("channels", {})

    ws.append(["COUNTERPARTY INTELLIGENCE & CHANNEL DISTRIBUTION", "", "", "", ""])
    ws.merge_cells("A1:E1")
    ws.cell(row=1, column=1).fill = HDR_FILL
    ws.cell(row=1, column=1).font = Font(name="Arial", size=11, bold=True, color="FFFFFF")

    ws.append(["", "", "", "", ""])
    ws.append(["Top Inward Counterparties — all payers except own accounts, related parties and lenders", "", "", "", ""])
    r1 = ws.max_row
    ws.cell(row=r1, column=1).fill = SEC_FILL
    ws.cell(row=r1, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r1}:E{r1}")

    ws.append(["Counterparty", "Txn Count", "Total Received", "Share of Gross Inflows", "Last Date"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    inward = cp_data.get("top_inward_parties", [])
    for p in inward[:10]:
        ws.append([p["counterparty"], p["count"], p["total_amount"], f"{p['share_pct']:.2f}%", p["last_date"]])
    # this table counts every credit; the scorecard's top-payer share counts eligible receipts only
    ws.append(["Note: shares here are of all credits. The Financial Profile's top-payer share is of eligible "
               "operating receipts (excludes personal, pass-through, bank-funded and unclassified credits).", "", "", "", ""])

    ws.append(["", "", "", "", ""])
    ws.append(["Top Outward Counterparties (Vendors / Payees)", "", "", "", ""])
    r2 = ws.max_row
    ws.cell(row=r2, column=1).fill = SEC_FILL
    ws.cell(row=r2, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r2}:E{r2}")

    ws.append(["Counterparty", "Txn Count", "Total Paid", "Share of Gross Outflows", "Last Date"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    outward = cp_data.get("top_outward_parties", [])
    for p in outward[:10]:
        ws.append([p["counterparty"], p["count"], p["total_amount"], f"{p['share_pct']:.2f}%", p["last_date"]])

    ws.append(["", "", "", "", ""])
    ws.append(["Transaction Channel Mix", "", "", "", ""])
    r3 = ws.max_row
    ws.cell(row=r3, column=1).fill = SEC_FILL
    ws.cell(row=r3, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r3}:E{r3}")

    ws.append(["Channel", "Txn Count", "Total Volume", "Share %", "Debit Volume"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    for ch in channels.get("channels", []):
        ws.append([ch["channel"], ch["total_count"], ch["total_amount"], f"{ch['volume_share_pct']:.2f}%", ch["debit_amount"]])

    col_widths = [35, 14, 18, 16, 16]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    for r in range(2, ws.max_row + 1):
        c1 = ws.cell(row=r, column=1)
        if c1.value and not c1.fill.fill_type:
            for c in range(1, 6):
                ws.cell(row=r, column=c).font = BODY
                ws.cell(row=r, column=c).border = THIN
            ws.cell(row=r, column=3).number_format = '#,##0.00;[Red]-#,##0.00'


def _write_risk_flags(ws, profile: dict):
    risk = profile.get("risk_analysis", {})
    fraud = profile.get("fraud_aml", {})

    ws.append(["RISK, BOUNCES & ANOMALY DETECTION REPORT", "", "", "", ""])
    ws.merge_cells("A1:E1")
    ws.cell(row=1, column=1).fill = HDR_FILL
    ws.cell(row=1, column=1).font = Font(name="Arial", size=11, bold=True, color="FFFFFF")

    ws.append(["", "", "", "", ""])
    ws.append(["1. Payment Bounces & Mandate Returns", "", "", "", ""])
    r1 = ws.max_row
    ws.cell(row=r1, column=1).fill = SEC_FILL
    ws.cell(row=r1, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r1}:E{r1}")

    ws.append(["Date", "Type", "Bounced Payment Amount", "Return Charge", "Narration", "Linked Loan", "Link Evidence"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    bounces = risk.get("bounces", [])
    if bounces:
        for b in bounces:
            charge = b.get("bounce_charge")
            ws.append([b["date"], b["type"], b.get("bounce_amount", "UNKNOWN"),
                       charge if charge is not None else "-", b["narration"],
                       b.get("linked_loan", "UNKNOWN"), b.get("loan_link_basis", "-")])
    else:
        ws.append(["-", "Zero Bounces Detected", "-", "-", "-", "", ""])

    ws.append(["", "", "", "", ""])
    ws.append(["2. Bank Penalty Charges & Fees", "", "", "", ""])
    r2 = ws.max_row
    ws.cell(row=r2, column=1).fill = SEC_FILL
    ws.cell(row=r2, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r2}:E{r2}")

    ws.append(["Date", "Penalty Fee", "Amount", "Narration", ""])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    penalties = risk.get("penalties", [])
    if penalties:
        for p in penalties:
            ws.append([p["date"], p.get("fee_type", "Bank Fee"), p["amount"], p["narration"], ""])
    else:
        ws.append(["-", "Zero Penalties Detected", "-", "-", ""])

    ws.append(["", "", "", "", ""])
    ws.append(["3. Potential Structuring / Threshold-Avoidance Patterns", "", "", "", ""])
    r3 = ws.max_row
    ws.cell(row=r3, column=1).fill = SEC_FILL
    ws.cell(row=r3, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r3}:E{r3}")

    ws.append(["Date", "Amount", "Threshold Avoided", "Confidence Level", "30-Day Frequency & Narration"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    struct_alerts = fraud.get("structuring_alerts", [])
    if struct_alerts:
        for sa in struct_alerts:
            ws.append([
                sa["date"],
                sa["amount"],
                f"{sa['threshold_avoided']} (gap: {sa['distance_pct']}%)",
                sa["confidence_level"],
                f"{sa['frequency_30d']} occurrences in 30d | {sa['narration']}"
            ])
    else:
        ws.append(["-", "-", "Zero Structuring Patterns", "LOW", "No threshold-avoidance patterns detected"])

    ws.append(["", "", "", "", ""])
    ws.append(["4. Rapid In-Out / Pass-Through Transactions (External and Related-Party)", "", "", "", ""])
    r4 = ws.max_row
    ws.cell(row=r4, column=1).fill = SEC_FILL
    ws.cell(row=r4, column=1).font = SEC_FONT
    ws.merge_cells(f"A{r4}:E{r4}")

    ws.append(["Credit Date", "Debit Date", "Amount (Cr/Dr)", "Confidence Level", "Gap Days & Narration", "Type"])
    _style_header(ws, row=ws.max_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    rapid = risk.get("rapid_in_out_cycles", [])
    if rapid:
        for r_item in rapid:
            ws.append([
                r_item["credit_date"],
                r_item["debit_date"],
                f"₹{r_item['credit_amount']:,.2f} / ₹{r_item['debit_amount']:,.2f}",
                r_item.get("confidence_level", "HIGH"),
                f"{r_item['gap_days']} days gap | {r_item['credit_narration']}",
                f"{r_item.get('pass_through_type', 'EXTERNAL')}: {r_item.get('counterparty', '-')} → "
                f"{r_item.get('debit_counterparty', '-')}",
            ])
    else:
        ws.append(["-", "-", "Zero Pass-Through Cycles", "-", ""])

    col_widths = [16, 18, 22, 18, 45, 28, 45]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    for r in range(2, ws.max_row + 1):
        c1 = ws.cell(row=r, column=1)
        if c1.value and not c1.fill.fill_type:
            # the bounce table is 7 columns wide, the other tables 5
            last = 7 if any(ws.cell(row=r, column=c).value not in (None, "") for c in (6, 7)) else 5
            for c in range(1, last + 1):
                ws.cell(row=r, column=c).font = BODY
                ws.cell(row=r, column=c).border = THIN


def _write_validation(ws, txns, issues, meta):
    ws.append(["Metric", "Value"])
    flagged = {i for i, _ in issues}
    dated_count = sum(1 for t in txns if t.get("txn_date") is not None)
    date_completeness = f"{(dated_count / max(1, len(txns))) * 100:.2f}%"
    narr_count = sum(1 for t in txns if (t.get("narration") or "").strip())
    narration_completeness = f"{(narr_count / max(1, len(txns))) * 100:.2f}%"

    _, field_summary = validate_field_linkage(txns)

    recon_val = f"{meta.get('recon', 0) * 100:.2f}%" if meta.get('recon', 0) > 0 else "0.00% (Direct print order passed)"
    for k, v in [
        ("Source file", meta.get("source")),
        ("Row assembly strategy", meta.get("strategy")),
        ("Chain orientation", meta.get("mode")),
        ("Rows extracted", len(txns)),
        ("Balance-chain pass rate", f"{meta.get('score', 0) * 100:.2f}%"),
        ("PDF field linkage pass rate", f"{field_summary['overall_accuracy'] * 100:.2f}%"),
        ("Date-field completeness", date_completeness),
        ("Narration-field completeness", narration_completeness),
        ("Rows flagged CHECK", len(flagged)),
        ("Out-of-order relinking needed", recon_val),
        ("Statement completeness", meta.get("completeness", "COMPLETE")),
    ]:
        ws.append([k, v])

    ws.append(["", ""])
    ws.append(["Row #", "Issue"])
    for i, msg in issues:
        ws.append([i + 1, msg])

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 70
    _style_header(ws)

    hdr2 = next((r for r in range(1, ws.max_row + 1)
                 if ws.cell(row=r, column=1).value == "Row #"), None)
    if hdr2:
        for c in (1, 2):
            cell = ws.cell(row=hdr2, column=c)
            cell.fill, cell.font = HDR_FILL, HDR_FONT

    for r in range(2, ws.max_row + 1):
        for c in (1, 2):
            if ws.cell(row=r, column=c).font.color is None:
                ws.cell(row=r, column=c).font = BODY
        if str(ws.cell(row=r, column=2).value or "").startswith(("BREAK", "MISSING_", "HEADER_")):
            ws.cell(row=r, column=2).fill = BAD
        if ws.cell(row=r, column=1).value in ("Date-field completeness", "Narration-field completeness", "PDF field linkage pass rate") and ws.cell(row=r, column=2).value != "100.00%":
            ws.cell(row=r, column=2).fill = WARN
        if ws.cell(row=r, column=1).value == "Statement completeness" and str(ws.cell(row=r, column=2).value or "").startswith("PARTIAL"):
            ws.cell(row=r, column=2).fill = WARN


def _write_pdf_field_validation(ws, txns):
    field_records, field_summary = validate_field_linkage(txns)

    ws.append(["Field Verification Metric", "Value"])
    for k, v in [
        ("Total Transactions Audited", len(txns)),
        ("Date Field Match Rate", f"{field_summary['date_accuracy'] * 100:.2f}%"),
        ("Narration Field Match Rate", f"{field_summary['narr_accuracy'] * 100:.2f}%"),
        ("Reference Field Match Rate", f"{field_summary['ref_accuracy'] * 100:.2f}%"),
        ("Debit Field Match Rate", f"{field_summary['debit_accuracy'] * 100:.2f}%"),
        ("Credit Field Match Rate", f"{field_summary['credit_accuracy'] * 100:.2f}%"),
        ("Balance Field Match Rate", f"{field_summary['balance_accuracy'] * 100:.2f}%"),
        ("Overall Field Linkage Accuracy", f"{field_summary['overall_accuracy'] * 100:.2f}%"),
    ]:
        ws.append([k, v])

    ws.append(["", ""])
    ws.append(["Txn #", "Page", "Date", "Narration", "Reference", "Debit", "Credit", "Balance", "Overall", "Mismatch Details"])
    tbl_hdr_row = ws.max_row

    for rec in field_records:
        ws.append([
            rec["txn_no"], rec["page"], rec["date_status"], rec["narr_status"],
            rec["ref_status"], rec["debit_status"], rec["credit_status"],
            rec["bal_status"], rec["overall_status"], rec["details"]
        ])

    _style_header(ws, row=1)
    for c in range(1, 11):
        cell = ws.cell(row=tbl_hdr_row, column=c)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    col_widths = {1: 8, 2: 8, 3: 12, 4: 14, 5: 14, 6: 12, 7: 12, 8: 14, 9: 12, 10: 40}
    for col_idx, w in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    dim_font = Font(name="Arial", size=10, color="888888")
    for row_idx in range(tbl_hdr_row + 1, ws.max_row + 1):
        for c in range(1, 11):
            cell = ws.cell(row=row_idx, column=c)
            cell.font = BODY
            if c in (1, 2, 3, 4, 5, 6, 7, 8, 9):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            if cell.value == "FAIL":
                cell.fill = BAD
                cell.font = Font(name="Arial", size=10, bold=True, color="9C0006")
            elif cell.value == "NA":
                cell.font = dim_font

    for r in range(2, 10):
        ws.cell(row=r, column=1).font = Font(name="Arial", size=10, bold=True)
        c2 = ws.cell(row=r, column=2)
        c2.font = BODY
        if ws.cell(row=r, column=1).value == "Overall Field Linkage Accuracy" and c2.value != "100.00%":
            c2.fill = WARN


def _write_calculation_reconciliation(ws, profile: dict, meta: dict, txns: list):
    exec_s = profile.get("executive_summary", {})
    el_inc = profile.get("eligible_income", {})
    debt = profile.get("debt_analysis", {})
    meta = meta or {}

    ws.append(["FINANCIAL CALCULATION RECONCILIATION & MATHEMATICAL AUDIT TRAIL", "", "", "", "", "", "", ""])
    ws.merge_cells("A1:H1")
    ws.cell(row=1, column=1).fill = HDR_FILL
    ws.cell(row=1, column=1).font = Font(name="Arial", size=12, bold=True, color="FFFFFF")

    ws.append(["", "", "", "", "", "", "", ""])
    ws.append(["Metric", "Formula Definition", "Input A", "Input B", "Calculated Value", "Reported Value", "Difference", "Audit Status"])
    hdr_row = ws.max_row
    _style_header(ws, row=hdr_row, fill=SUB_HDR_FILL, font=SUB_HDR_FONT)

    m_elig = el_inc.get("monthly_eligible_income", 0.0)
    m_op_exp = el_inc.get("monthly_operating_expenses", 0.0)
    m_debt_srv = debt.get("total_monthly_debt_service", 0.0)
    m_emi = debt.get("monthly_emi_paid", 0.0)
    m_interest = debt.get("total_monthly_interest_obligation", 0.0)
    m_op_cash = exec_s.get("monthly_operating_cash_available", 0.0)
    m_surplus = exec_s.get("estimated_monthly_operating_surplus", 0.0)

    # 1. Operating Cash Available (CADS)
    calc_op_cash = round(m_elig - m_op_exp, 2)
    rep_op_cash = round(m_op_cash, 2)
    diff_op_cash = round(calc_op_cash - rep_op_cash, 2)
    stat_op_cash = "PASS" if abs(diff_op_cash) < 0.05 else "FAIL"

    # 2. Total Monthly Debt Service
    calc_debt_srv = round(m_emi + m_interest, 2)
    rep_debt_srv = round(m_debt_srv, 2)
    diff_debt_srv = round(calc_debt_srv - rep_debt_srv, 2)
    stat_debt_srv = "PASS" if abs(diff_debt_srv) < 0.05 else "FAIL"

    # 3. Monthly Operating Surplus (Post-Debt)
    calc_surplus = round(calc_op_cash - rep_debt_srv, 2)
    rep_surplus = round(m_surplus, 2)
    diff_surplus = round(calc_surplus - rep_surplus, 2)
    stat_surplus = "PASS" if abs(diff_surplus) < 0.05 else "FAIL"

    # 4. Business Debt Service / Revenue Ratio (or FOIR)
    debt_label = debt.get("debt_ratio_label", "Business Debt Service / Revenue Ratio")
    calc_ratio = round((rep_debt_srv / m_elig * 100.0) if m_elig > 0 else 0.0, 2)
    rep_ratio = round(debt.get("foir_percentage") or 0.0, 2)
    diff_ratio = round(calc_ratio - rep_ratio, 2)
    stat_ratio = "PASS" if abs(diff_ratio) < 0.05 else "FAIL"
    # suppressed on near-zero income: nothing to reconcile
    ratio_cells = ((f"{calc_ratio:.2f}%", f"{rep_ratio:.2f}%", f"{diff_ratio:.2f}%", stat_ratio)
                   if debt.get("foir_percentage") is not None else ("N/M", "N/M", "-", "N/M (no meaningful income)"))

    obs_monthly = el_inc.get("observed_monthly_eligible_receipts", m_elig)
    input_b_ratio = f"₹ {m_elig:,.2f}" if obs_monthly == m_elig else f"UW Baseline: ₹ {m_elig:,.2f} (Obs: ₹ {obs_monthly:,.2f})"

    # 5. Debt Service Coverage Ratio (DSCR)
    rep_dscr = debt.get("dscr")
    if rep_debt_srv == 0:
        calc_dscr_str = "N/A (Debt Free)"
        rep_dscr_str = debt.get("dscr_display", "N/A — No Debt Service")
        diff_dscr_str = "0.00"
        stat_dscr = "PASS"
    elif calc_op_cash < 0:
        calc_dscr_str = "N/M (Negative Op Cash)"
        rep_dscr_str = debt.get("dscr_display", "N/M")
        diff_dscr_str = "0.00"
        stat_dscr = "PASS"
    else:
        calc_dscr = round(calc_op_cash / rep_debt_srv, 2)
        calc_dscr_str = f"{calc_dscr:.2f}x"
        rep_dscr_str = f"{rep_dscr:.2f}x" if rep_dscr is not None else "N/A"
        diff_dscr = round(calc_dscr - (rep_dscr or 0.0), 2)
        diff_dscr_str = f"{diff_dscr:.2f}"
        stat_dscr = "PASS" if abs(diff_dscr) < 0.05 else "FAIL"

    # 6. Operating Cash Coverage
    rep_cov = debt.get("operating_cash_coverage_ratio")
    if rep_debt_srv == 0:
        calc_cov_str = "N/A (Debt Free)"
        rep_cov_str = debt.get("operating_cash_coverage_status", "DEBT_FREE")
        diff_cov_str = "0.00"
        stat_cov = "PASS"
    elif debt.get("operating_cash_coverage_status") == "RETAIL_ACCOUNT":
        calc_cov_str = "N/A (Retail Account)"
        rep_cov_str = "N/A (Retail Account)"
        diff_cov_str = "0.00"
        stat_cov = "PASS"
    else:
        calc_cov = round(calc_op_cash / rep_debt_srv, 2)
        calc_cov_str = f"{calc_cov:.2f}x"
        rep_cov_str = f"{rep_cov:.2f}x" if rep_cov is not None else "N/A"
        diff_cov = round(calc_cov - (rep_cov or 0.0), 2)
        diff_cov_str = f"{diff_cov:.2f}"
        stat_cov = "PASS" if abs(diff_cov) < 0.05 else "FAIL"

    # 7. Total Debt Burden Percentage
    calc_burden = round((rep_debt_srv / m_elig * 100.0) if m_elig > 0 else 0.0, 2)
    rep_burden = round(debt.get("debt_burden_percentage") or 0.0, 2)
    diff_burden = round(calc_burden - rep_burden, 2)
    stat_burden = "PASS" if abs(diff_burden) < 0.05 else "FAIL"
    burden_cells = ((f"{calc_burden:.2f}%", f"{rep_burden:.2f}%", f"{diff_burden:.2f}%", stat_burden)
                    if debt.get("debt_burden_percentage") is not None else ("N/M", "N/M", "-", "N/M (no meaningful income)"))

    # 8. Running Balance Chain Continuity
    score = meta.get("score", 1.0)
    score_pct = round(score * 100.0, 2)
    calc_chain = "100.00%"
    rep_chain = f"{score_pct:.2f}%"
    diff_chain = f"{round(100.0 - score_pct, 2):.2f}%"
    stat_chain = "PASS" if score >= 0.999 else "FAIL"

    rows = [
        ("Operating Cash Available (CADS)", "Eligible Receipts − Operating Expenses",
         f"₹ {m_elig:,.2f}", f"₹ {m_op_exp:,.2f}", f"₹ {calc_op_cash:,.2f}", f"₹ {rep_op_cash:,.2f}", f"₹ {diff_op_cash:,.2f}", stat_op_cash),

        ("Total Monthly Debt Service", "EMIs Paid per Month + Financing/OD Interest",
         f"₹ {m_emi:,.2f}", f"₹ {m_interest:,.2f}", f"₹ {calc_debt_srv:,.2f}", f"₹ {rep_debt_srv:,.2f}", f"₹ {diff_debt_srv:,.2f}", stat_debt_srv),

        ("Operating Surplus (Post-Debt)", "Operating Cash Available − Total Debt Service",
         f"₹ {calc_op_cash:,.2f}", f"₹ {rep_debt_srv:,.2f}", f"₹ {calc_surplus:,.2f}", f"₹ {rep_surplus:,.2f}", f"₹ {diff_surplus:,.2f}", stat_surplus),

        (debt_label, "(Total Debt Service / Underwriting Baseline) × 100",
         f"₹ {rep_debt_srv:,.2f}", input_b_ratio, *ratio_cells),

        ("Debt Service Coverage Ratio (DSCR)", "Operating Cash Available / Total Debt Service",
         f"₹ {calc_op_cash:,.2f}", f"₹ {rep_debt_srv:,.2f}", calc_dscr_str, rep_dscr_str, diff_dscr_str, stat_dscr),

        ("Operating Cash Coverage", "Operating Cash Available / Total Debt Service",
         f"₹ {calc_op_cash:,.2f}", f"₹ {rep_debt_srv:,.2f}", calc_cov_str, rep_cov_str, diff_cov_str, stat_cov),

        ("Total Debt Burden Percentage", "(Total Debt Service / Eligible Receipts) × 100",
         f"₹ {rep_debt_srv:,.2f}", f"₹ {m_elig:,.2f}", *burden_cells),

        ("Balance Chain Continuity", "Prior Balance + Credit − Debit == Balance",
         f"{len(txns)} Rows", "0 Breaks", calc_chain, rep_chain, diff_chain, stat_chain),
    ]

    for r in rows:
        ws.append(list(r))

    col_widths = [36, 46, 22, 22, 22, 22, 16, 14]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    pass_fill = PatternFill("solid", fgColor="C6EFCE")
    pass_font = Font(name="Arial", size=10, bold=True, color="006100")
    fail_fill = PatternFill("solid", fgColor="FFC7CE")
    fail_font = Font(name="Arial", size=10, bold=True, color="9C0006")

    for r in range(hdr_row + 1, ws.max_row + 1):
        for c in range(1, 9):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY
            cell.border = THIN
            if c in (3, 4, 5, 6, 7):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif c == 8:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if cell.value == "PASS":
                    cell.fill = pass_fill
                    cell.font = pass_font
                else:
                    cell.fill = fail_fill
                    cell.font = fail_font
