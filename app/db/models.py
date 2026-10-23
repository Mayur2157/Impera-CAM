"""ORM models.

Tables
------
tenants         — one per customer organisation (isolates all data)
users           — login accounts; each belongs to exactly one tenant
jobs            — processing run (one or many PDFs)
file_tasks      — one row per PDF inside a job
account_registry— cross-statement linking data, scoped to a tenant
usage           — billing meter: one row per completed file_task
api_keys        — customer API keys (only a SHA-256 of the secret is stored)
invites         — pending invitations into a tenant (only a SHA-256 of the token)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class Tenant(Base):
    __tablename__ = "tenants"

    id         = Column(String(36),  primary_key=True, default=_uuid)
    name       = Column(String(255), nullable=False)
    plan       = Column(String(50),  default="free")   # free | starter | pro
    max_files  = Column(Integer,     default=10)
    max_upload_mb = Column(Integer,  default=20)
    monthly_statement_quota = Column(Integer, nullable=True)   # None = unlimited
    status     = Column(String(20),  default="active")  # active | suspended
    created_at = Column(DateTime,    default=datetime.utcnow)

    users    = relationship("User",            back_populates="tenant", cascade="all, delete-orphan")
    jobs     = relationship("Job",             back_populates="tenant", cascade="all, delete-orphan")
    # not "registry": SQLAlchemy reserves that name on declarative classes
    account_registry = relationship("AccountRegistry", back_populates="tenant",
                                    cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id              = Column(String(36),  primary_key=True, default=_uuid)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean,     default=True)
    is_superuser    = Column(Boolean,     default=False)
    tenant_id       = Column(String(36),  ForeignKey("tenants.id"), nullable=False, index=True)
    role            = Column(String(50),  default="member")  # owner | admin | member
    created_at      = Column(DateTime,    default=datetime.utcnow)
    last_login_at   = Column(DateTime,    nullable=True)
    terms_accepted_at = Column(DateTime,  nullable=True)
    # a removed member keeps the row (jobs reference it) but loses their
    # personal data: email anonymised, password cleared
    removed_at      = Column(DateTime,    nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    jobs   = relationship("Job",    back_populates="user")


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class Job(Base):
    """One extraction run submitted by a user.

    The PDF password is NEVER stored here — it lives in memory only for the
    duration of the thread-pool worker, then is discarded.
    """
    __tablename__ = "jobs"

    id         = Column(String(36),  primary_key=True, default=_short_id)
    tenant_id  = Column(String(36),  ForeignKey("tenants.id"), nullable=False, index=True)
    user_id    = Column(String(36),  ForeignKey("users.id"),   nullable=False)
    status     = Column(String(50),  default="queued")          # queued|running|done|error
    use_ocr    = Column(Boolean,     default=True)
    dpi        = Column(Integer,     default=300)
    bank       = Column(String(100), nullable=True)
    # set when a customer's system submitted the job with an API key
    api_key_id = Column(String(36),  ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime,    default=datetime.utcnow, index=True)

    tenant     = relationship("Tenant",    back_populates="jobs")
    user       = relationship("User",      back_populates="jobs")
    file_tasks = relationship("FileTask",  back_populates="job",
                              cascade="all, delete-orphan", order_by="FileTask.position")
    # billing rows outlive the job: the FK is ON DELETE SET NULL, so purging a
    # job never deletes what it metered
    usage      = relationship("Usage",     back_populates="job",  passive_deletes=True)


# ---------------------------------------------------------------------------
# FileTask
# ---------------------------------------------------------------------------

class FileTask(Base):
    __tablename__ = "file_tasks"

    id          = Column(String(36),   primary_key=True, default=_uuid)
    job_id      = Column(String(36),   ForeignKey("jobs.id"), nullable=False, index=True)
    position    = Column(Integer,      default=0)         # upload order within the job
    name        = Column(String(500),  nullable=False)
    path        = Column(String(1000), nullable=False)    # relative to settings.upload_dir
    status      = Column(String(50),   default="queued", index=True)  # queued|running|done|error
    progress    = Column(Integer,      default=0)
    message     = Column(Text,         nullable=True)
    result_data = Column(JSON,         nullable=True)  # dict from pipeline.process()
    error       = Column(Text,         nullable=True)
    started_at  = Column(DateTime,     nullable=True)
    finished_at = Column(DateTime,     nullable=True)

    job = relationship("Job", back_populates="file_tasks")


# ---------------------------------------------------------------------------
# Account registry (per-tenant)
# ---------------------------------------------------------------------------

class AccountRegistry(Base):
    """Cross-statement link memory, scoped to a tenant so Customer A's
    holders never appear as related parties for Customer B's analysis."""

    __tablename__ = "account_registry"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_number", name="uq_tenant_account"),
        {"mysql_engine": "InnoDB"},
    )

    id             = Column(String(36),  primary_key=True, default=_uuid)
    tenant_id      = Column(String(36),  ForeignKey("tenants.id"), nullable=False, index=True)
    account_number = Column(String(100), nullable=False)
    customer_name  = Column(String(500), nullable=True)
    bank           = Column(String(255), nullable=True)
    email          = Column(String(255), nullable=True)
    phone          = Column(String(20),  nullable=True)
    address        = Column(Text,        nullable=True)

    tenant = relationship("Tenant", back_populates="account_registry")


# ---------------------------------------------------------------------------
# Usage / billing meter
# ---------------------------------------------------------------------------

class Usage(Base):
    __tablename__ = "usage"

    id         = Column(String(36), primary_key=True, default=_uuid)
    tenant_id  = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id    = Column(String(36), ForeignKey("users.id"),   nullable=False)
    job_id     = Column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    pages      = Column(Integer,    default=0)
    statements = Column(Integer,    default=1)
    created_at = Column(DateTime,   default=datetime.utcnow, index=True)

    job = relationship("Job", back_populates="usage")


# ---------------------------------------------------------------------------
# API keys — how customers' systems call /api/v1
# ---------------------------------------------------------------------------

class ApiKey(Base):
    """The secret is shown once at creation; only its SHA-256 is kept."""

    __tablename__ = "api_keys"

    id           = Column(String(36),  primary_key=True, default=_uuid)
    tenant_id    = Column(String(36),  ForeignKey("tenants.id"), nullable=False, index=True)
    created_by   = Column(String(36),  ForeignKey("users.id"), nullable=False)
    name         = Column(String(100), nullable=False)
    prefix       = Column(String(20),  nullable=False)        # icam_live_Ab12 — safe to display
    key_hash     = Column(String(64),  nullable=False, unique=True, index=True)
    scopes       = Column(JSON,        nullable=False)        # ["jobs:read", "jobs:write"]
    created_at   = Column(DateTime,    default=datetime.utcnow)
    last_used_at = Column(DateTime,    nullable=True)
    revoked_at   = Column(DateTime,    nullable=True)

    creator = relationship("User")


# ---------------------------------------------------------------------------
# Invites — join an organisation with a one-time link
# ---------------------------------------------------------------------------

class Invite(Base):
    __tablename__ = "invites"

    id          = Column(String(36),  primary_key=True, default=_uuid)
    tenant_id   = Column(String(36),  ForeignKey("tenants.id"), nullable=False, index=True)
    email       = Column(String(255), nullable=False)
    role        = Column(String(50),  nullable=False)         # admin | member
    token_hash  = Column(String(64),  nullable=False, unique=True, index=True)
    created_by  = Column(String(36),  ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime,    default=datetime.utcnow)
    expires_at  = Column(DateTime,    nullable=False)
    accepted_at = Column(DateTime,    nullable=True)

    tenant = relationship("Tenant")
