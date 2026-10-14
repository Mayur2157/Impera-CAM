"""ORM models.

Tables
------
tenants         — one per customer organisation (isolates all data)
users           — login accounts; each belongs to exactly one tenant
jobs            — processing run (one or many PDFs)
file_tasks      — one row per PDF inside a job
account_registry— cross-statement linking data, scoped to a tenant
usage           — billing meter: one row per completed file_task
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
    created_at = Column(DateTime,    default=datetime.utcnow)

    users    = relationship("User",            back_populates="tenant", cascade="all, delete-orphan")
    jobs     = relationship("Job",             back_populates="tenant", cascade="all, delete-orphan")
    registry = relationship("AccountRegistry", back_populates="tenant", cascade="all, delete-orphan")


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
    role            = Column(String(50),  default="admin")   # admin | member
    created_at      = Column(DateTime,    default=datetime.utcnow)

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
    created_at = Column(DateTime,    default=datetime.utcnow, index=True)

    tenant     = relationship("Tenant",    back_populates="jobs")
    user       = relationship("User",      back_populates="jobs")
    file_tasks = relationship("FileTask",  back_populates="job",
                              cascade="all, delete-orphan", order_by="FileTask.id")
    usage      = relationship("Usage",     back_populates="job",  cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# FileTask
# ---------------------------------------------------------------------------

class FileTask(Base):
    __tablename__ = "file_tasks"

    id          = Column(String(36),   primary_key=True, default=_uuid)
    job_id      = Column(String(36),   ForeignKey("jobs.id"), nullable=False, index=True)
    name        = Column(String(500),  nullable=False)
    path        = Column(String(1000), nullable=False)
    status      = Column(String(50),   default="queued")
    progress    = Column(Integer,      default=0)
    message     = Column(Text,         nullable=True)
    result_data = Column(JSON,         nullable=True)  # dict from pipeline.process()
    error       = Column(Text,         nullable=True)

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

    tenant = relationship("Tenant", back_populates="registry")


# ---------------------------------------------------------------------------
# Usage / billing meter
# ---------------------------------------------------------------------------

class Usage(Base):
    __tablename__ = "usage"

    id         = Column(String(36), primary_key=True, default=_uuid)
    tenant_id  = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id    = Column(String(36), ForeignKey("users.id"),   nullable=False)
    job_id     = Column(String(36), ForeignKey("jobs.id"),    nullable=True)
    pages      = Column(Integer,    default=0)
    statements = Column(Integer,    default=1)
    created_at = Column(DateTime,   default=datetime.utcnow)

    job = relationship("Job", back_populates="usage")
