"""Command line entry point.

    python cli.py "statements/*.pdf" -o output/ [--password X] [--no-ocr] [--dpi 300]
"""
import argparse, glob, os, sys

from app.config import settings
from app.core.pipeline import process


def main():
    ap = argparse.ArgumentParser(description="Bank statement PDF -> Excel")
    ap.add_argument("pattern", help='glob of PDFs, e.g. "statements/*.pdf"')
    ap.add_argument("-o", "--out", default=settings.output_dir)
    ap.add_argument("--password", default=None)
    ap.add_argument("--no-ocr", action="store_true", help="skip scanned pages")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--backend", choices=["paddle", "tesseract"], default=None)
    ap.add_argument("--bank", default=None,
                    help="bank name for statements that print it only as a logo")
    a = ap.parse_args()

    files = sorted(glob.glob(a.pattern))
    if not files:
        print(f"no files matched {a.pattern}", file=sys.stderr)
        return 1
    os.makedirs(a.out, exist_ok=True)
    bad = 0
    for f in files:
        try:
            clean_name = os.path.basename(f)
            r = process(f, a.out, password=a.password, use_ocr=not a.no_ocr,
                        dpi=a.dpi, backend=a.backend, source_name=clean_name, bank=a.bank)
            p_flag = " [PARTIAL]" if r.get("is_partial") else ""
            print(f"{clean_name[:44]:46s} rows={r['rows']:5d} "
                  f"chain={r['chain'] * 100:6.2f}%  flags={r['flagged']:3d}  "
                  f"{r['info'].get('bank', '?')}{p_flag}")
            fp = r.get("financial_profile")
            if fp:
                foir = fp.get("foir_percentage")
                foir_txt = f"{foir:.1f}%" if foir is not None else "N/M"
                print(f"  └─► CAM Profile: Score={fp.get('credit_score_index', 0)}/100 ({fp.get('risk_rating')}) | "
                      f"ABB=₹{fp.get('abb', 0):,.2f} | NetFlow=₹{fp.get('net_cash_flow', 0):,.2f} | "
                      f"FOIR={foir_txt} | Bounces={fp.get('outward_bounces', 0)}")
        except Exception as e:                          # noqa: BLE001
            bad += 1
            print(f"{os.path.basename(f)[:44]:46s} ERROR {type(e).__name__}: {e}",
                  file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
