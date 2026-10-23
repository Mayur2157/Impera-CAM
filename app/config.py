"""Runtime settings.  Override any of these with environment variables.

Local development needs none of these: the database is a SQLite file in
data/ and jobs run inside the API process (BSX_QUEUE=local).

BSX_MYSQL_URL         full SQLAlchemy URL; default sqlite:///data/impera_cam.db
                        e.g. mysql+pymysql://user:password@host:3307/impera_cam
BSX_QUEUE             local  — jobs run on threads inside the API (default)
                      celery — jobs go through Redis to separate Celery workers
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


def _origins(name, default) -> tuple[str, ...]:
    # a tuple, not a list: a frozen dataclass rejects mutable defaults (Python 3.11+)
    raw = _str(name, default)
    return tuple(o.strip() for o in raw.split(",") if o.strip())


@dataclass(frozen=True)
class Settings:
    # --- deployment: "prod" refuses to start on development defaults ---
    env: str = _str("BSX_ENV", "dev").lower()

    # --- storage ---
    upload_dir: str = _dir("BSX_UPLOAD_DIR", "data/uploads")
    output_dir: str = _dir("BSX_OUTPUT_DIR", "output")

    # --- database: a local SQLite file unless a server URL is given ---
    mysql_url: str = _str(
        "BSX_MYSQL_URL",
        "sqlite:///" + os.path.join(_ROOT, "data", "impera_cam.db").replace("\\", "/"),
    )
    # per process: size the API and each worker so their sum stays under
    # MySQL max_connections
    db_pool_size: int = _int("BSX_DB_POOL_SIZE", 10)
    db_max_overflow: int = _int("BSX_DB_MAX_OVERFLOW", 10)

    # --- queue: "local" threads in the API process, or "celery" workers via Redis ---
    queue_mode: str = _str("BSX_QUEUE", "local").lower()
    local_workers: int = _int("BSX_LOCAL_WORKERS", 2)      # digital files at once (local)
    # Celery broker, rate-limit counters and worker heartbeats (celery mode only)
    redis_url: str = _str("BSX_REDIS_URL", "redis://localhost:6379/0")

    # --- JSON registry: CLI runs only (no tenant); the web path uses MySQL ---
    registry_path: str = _dir("BSX_REGISTRY_PATH", "data/account_registry.json")

    # --- auth ---
    jwt_secret: str = _str("BSX_JWT_SECRET", "CHANGE-ME-USE-A-RANDOM-32-CHAR-STRING")
    jwt_expire_hours: int = _int("BSX_JWT_EXPIRE_HOURS", 24)

    # --- uploads ---
    max_upload_mb: int = _int("BSX_MAX_UPLOAD_MB", 40)
    max_files: int = _int("BSX_MAX_FILES", 25)

    # --- workers ---
    workers: int = _int("BSX_WORKERS", 4)      # reported by /api/health only
    retention_seconds: int = _int("BSX_RETENTION_SECONDS", 6 * 3600)
    purge_interval_seconds: int = _int("BSX_PURGE_INTERVAL_SECONDS", 900)
    # time limits per file; the hard limit kills a pathological PDF
    task_cpu_soft_seconds: int = _int("BSX_TASK_CPU_SOFT_SECONDS", 600)
    task_cpu_hard_seconds: int = _int("BSX_TASK_CPU_HARD_SECONDS", 720)
    task_ocr_soft_seconds: int = _int("BSX_TASK_OCR_SOFT_SECONDS", 1800)
    task_ocr_hard_seconds: int = _int("BSX_TASK_OCR_HARD_SECONDS", 2100)
    # a file whose worker died (crash, OOM) is redelivered after this long; it
    # must exceed the longest hard limit or a slow OCR file would run twice
    broker_visibility_seconds: int = _int("BSX_BROKER_VISIBILITY_SECONDS", 2400)

    # --- public URL of the portal (invite links point here) ---
    public_url: str = _str("BSX_PUBLIC_URL", "http://localhost:8000").rstrip("/")

    # --- fairness and abuse limits ---
    tenant_max_active_files: int = _int("BSX_TENANT_MAX_ACTIVE_FILES", 50)
    api_key_per_minute: int = _int("BSX_API_KEY_PER_MINUTE", 120)
    login_per_minute: int = _int("BSX_LOGIN_PER_MINUTE", 10)
    register_per_hour: int = _int("BSX_REGISTER_PER_HOUR", 5)

    # --- OCR ---
    ocr_backend: str = _str("BSX_OCR_BACKEND", "paddle")
    ocr_device: str = _str("BSX_OCR_DEVICE", "gpu")
    ocr_gpu_id: int = _int("BSX_OCR_GPU_ID", 0)

    # --- CORS (lock this down in production!) ---
    allowed_origins: tuple = _origins("BSX_ALLOWED_ORIGINS", "*")


settings = Settings()
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)


def production_problems(s: Settings = settings) -> list[str]:
    """Development defaults that must never reach an external deployment."""
    problems = []
    if len(s.jwt_secret) < 32 or s.jwt_secret.upper().startswith("CHANGE"):
        problems.append("BSX_JWT_SECRET is a placeholder or shorter than 32 characters")
    if "*" in s.allowed_origins:
        problems.append("BSX_ALLOWED_ORIGINS must list exact origins, not *")
    if "://root:" in s.mysql_url:
        problems.append("BSX_MYSQL_URL connects as the MySQL root user")
    if s.mysql_url.startswith("sqlite"):
        problems.append("BSX_MYSQL_URL is the local SQLite file; use a database server")
    if s.queue_mode != "celery":
        problems.append("BSX_QUEUE must be celery: local mode runs jobs inside the API process")
    return problems
