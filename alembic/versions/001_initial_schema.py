"""Initial SaaS schema — tenants, users, jobs, file_tasks, account_registry, usage.

Revision ID: 001
Revises:
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id",            sa.String(36),  primary_key=True),
        sa.Column("name",          sa.String(255), nullable=False),
        sa.Column("plan",          sa.String(50),  server_default="free"),
        sa.Column("max_files",     sa.Integer(),   server_default="10"),
        sa.Column("max_upload_mb", sa.Integer(),   server_default="20"),
        sa.Column("created_at",    sa.DateTime(),  nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "users",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("email",           sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active",       sa.Boolean(),   server_default="1"),
        sa.Column("is_superuser",    sa.Boolean(),   server_default="0"),
        sa.Column("tenant_id",       sa.String(36),  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("role",            sa.String(50),  server_default="admin"),
        sa.Column("created_at",      sa.DateTime(),  nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_users_email",     "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "jobs",
        sa.Column("id",         sa.String(36),  primary_key=True),
        sa.Column("tenant_id",  sa.String(36),  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id",    sa.String(36),  sa.ForeignKey("users.id"),   nullable=False),
        sa.Column("status",     sa.String(50),  server_default="queued"),
        sa.Column("use_ocr",    sa.Boolean(),   server_default="1"),
        sa.Column("dpi",        sa.Integer(),   server_default="300"),
        sa.Column("bank",       sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(),  nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_jobs_tenant_id",  "jobs", ["tenant_id"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    op.create_table(
        "file_tasks",
        sa.Column("id",          sa.String(36),   primary_key=True),
        sa.Column("job_id",      sa.String(36),   sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("name",        sa.String(500),  nullable=False),
        sa.Column("path",        sa.String(1000), nullable=False),
        sa.Column("status",      sa.String(50),   server_default="queued"),
        sa.Column("progress",    sa.Integer(),    server_default="0"),
        sa.Column("message",     sa.Text(),       nullable=True),
        sa.Column("result_data", sa.JSON(),       nullable=True),
        sa.Column("error",       sa.Text(),       nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_file_tasks_job_id", "file_tasks", ["job_id"])

    op.create_table(
        "account_registry",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("tenant_id",      sa.String(36),  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_number", sa.String(100), nullable=False),
        sa.Column("customer_name",  sa.String(500), nullable=True),
        sa.Column("bank",           sa.String(255), nullable=True),
        sa.Column("email",          sa.String(255), nullable=True),
        sa.Column("phone",          sa.String(20),  nullable=True),
        sa.Column("address",        sa.Text(),      nullable=True),
        sa.UniqueConstraint("tenant_id", "account_number", name="uq_tenant_account"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_account_registry_tenant_id", "account_registry", ["tenant_id"])

    op.create_table(
        "usage",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("tenant_id",  sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id",    sa.String(36), sa.ForeignKey("users.id"),   nullable=False),
        sa.Column("job_id",     sa.String(36), sa.ForeignKey("jobs.id"),    nullable=True),
        sa.Column("pages",      sa.Integer(),  server_default="0"),
        sa.Column("statements", sa.Integer(),  server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_usage_tenant_id", "usage", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("usage")
    op.drop_table("account_registry")
    op.drop_table("file_tasks")
    op.drop_table("jobs")
    op.drop_table("users")
    op.drop_table("tenants")
