"""Project entry point.

    python main.py
    python main.py --reload
    python main.py --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import argparse
import os

import uvicorn

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Bank statement extractor web UI")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true", help="reload on code changes")
    a = ap.parse_args()

    os.chdir(ROOT)
    from app.core.ocr import probe
    p = probe()
    gpu = p.get("gpu") or "not seen"
    print(f"OCR backend={p['backend'] or 'none'}  "
          f"device={p['device'] or '-'}  gpu={gpu}")
    if p.get("warning"):
        print(f"OCR warning: {p['warning']}")
    uvicorn.run("app.main:app", host=a.host, port=a.port, reload=a.reload)


if __name__ == "__main__":
    main()
