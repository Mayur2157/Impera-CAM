"""Runtime settings.  Override any of these with environment variables.

New SaaS settings
-----------------
BSX_MYSQL_URL         full SQLAlchemy URL, e.g.
                        mysql+pymysql://user:password@localhost/impera_cam
BSX_JWT_SECRET        random string, at least 32 chars — CHANGE IN PRODUCTION
BSX_JWT_EXPIRE_HOURS  token lifetime (default 24 h)
BSX_ALLOWED_ORIGINS   comma-separated list of allowed CORS origins
                        e.g. https://app.imperacam.com,https://staging.imperacam.com
                        Defaults to * in dev mode, MUST be restricted in production.
"""
import os
from dataclasses import dataclass


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _dir(name, default):
    v = os.environ.get(name, default)
    return v if os.path.isabs(v) else os.path.join(_ROOT, v)


def _str(name, default):
    v = os.environ.get(name)
    return default if v is None or v.strip() == "" else v.strip()


def _origins(name, default) -> list[str]:
    raw = _str(name, default)
    return [o.strip() for o in raw.split(",") if o.strip()]


@dataclass(frozen=True)
class Settings:
    # --- storage ---
    upload_dir: str = _dir("BSX_UPLOAD_DIR", "data/uploads")
    output_dir: str = _dir("BSX_OUTPUT_DIR", "output")

    # --- database ---
    mysql_url: str = _str(
        "BSX_MYSQL_URL",
        "mysql+pymysql://root:password@localhost/impera_cam",
    )

    # --- legacy JSON registry (used only if mysql_url is unavailable) ---
    registry_path: str = _dir("BSX_REGISTRY_PATH", "data/account_registry.json")

    # --- auth ---
    jwt_secret: str = _str("BSX_JWT_SECRET", "CHANGE-ME-USE-A-RANDOM-32-CHAR-STRING")
    jwt_expire_hours: int = _int("BSX_JWT_EXPIRE_HOURS", 24)

    # --- uploads ---
    max_upload_mb: int = _int("BSX_MAX_UPLOAD_MB", 40)
    max_files: int = _int("BSX_MAX_FILES", 25)

    # --- workers ---
    workers: int = _int("BSX_WORKERS", 4)
    retention_seconds: int = _int("BSX_RETENTION_SECONDS", 6 * 3600)

    # --- OCR ---
    ocr_backend: str = _str("BSX_OCR_BACKEND", "paddle")
    ocr_device: str = _str("BSX_OCR_DEVICE", "gpu")
    ocr_gpu_id: int = _int("BSX_OCR_GPU_ID", 0)

    # --- CORS (lock this down in production!) ---
    allowed_origins: list = _origins("BSX_ALLOWED_ORIGINS", "*")


settings = Settings()
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)
