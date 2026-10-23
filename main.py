"""Project entry point.

    python main.py
    python main.py --reload
    python main.py --host 127.0.0.1 --port 8000

Brings the database schema up to date (Alembic), then serves the API and the
portal. With the defaults everything runs in this one process: a SQLite file
in data/ and jobs on local threads (see app/config.py: BSX_QUEUE).
"""
from __future__ import annotations

import argparse
import os

import uvicorn

ROOT = os.path.dirname(os.path.abspath(__file__))


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(os.path.join(ROOT, "alembic.ini")), "head")


def main():
    ap = argparse.ArgumentParser(description="Impera CAM API and portal")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true",
                    help="reload on code changes (a reload fails files still processing)")
    a = ap.parse_args()

    os.chdir(ROOT)
    from app.config import settings
    url = settings.mysql_url
    db = f"SQLite {url.split(':///', 1)[1]}" if url.startswith("sqlite") else url.split("@")[-1]
    print(f"Database={db}  queue={settings.queue_mode}")
    migrate()

    from app.core.ocr import probe
    p = probe()
    gpu = p.get("gpu") or "not seen"
    print(f"OCR backend={p['backend'] or 'none'}  "
          f"device={p['device'] or '-'}  gpu={gpu}")
    if p.get("warning"):
        print(f"OCR warning: {p['warning']}")
    portal = os.path.isdir(os.path.join(ROOT, "frontend", "dist"))
    print(f"Portal: http://localhost:{a.port}/" if portal else
          "Portal not built: run `npm run build` in frontend/, or `npm run dev` there (port 5173)")
    uvicorn.run("app.main:app", host=a.host, port=a.port, reload=a.reload)


if __name__ == "__main__":
    main()
