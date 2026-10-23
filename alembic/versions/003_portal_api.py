"""Customer portal + public API — API keys, invites, roles, suspension, quotas.

* api_keys, invites                     new tables (only hashes of secrets/tokens)
* tenants.status, monthly_statement_quota
* users.last_login_at, terms_accepted_at, removed_at; roles owner|admin|member
  (the earliest admin of every existing tenant becomes its owner)
* jobs.api_key_id, usage.api_key_id     which key submitted / metered the work
* index on usage.created_at             usage reports by date range

Revision ID: 003
Revises: 002
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("tenant_id",    sa.String(36),  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_by",   sa.String(36),  sa.ForeignKey("users.id"),   nullable=False),
        sa.Column("name",         sa.String(100), nullable=False),
        sa.Column("prefix",       sa.String(20),  nullable=False),
        sa.Column("key_hash",     sa.String(64),  nullable=False),
        sa.Column("scopes",       sa.JSON(),      nullable=False),
        sa.Column("created_at",   sa.DateTime(),  nullable=True),
        sa.Column("last_used_at", sa.DateTime(),  nullable=True),
        sa.Column("revoked_at",   sa.DateTime(),  nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "invites",
        sa.Column("id",          sa.String(36),  primary_key=True),
        sa.Column("tenant_id",   sa.String(36),  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email",       sa.String(255), nullable=False),
        sa.Column("role",        sa.String(50),  nullable=False),
        sa.Column("token_hash",  sa.String(64),  nullable=False),
        sa.Column("created_by",  sa.String(36),  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at",  sa.DateTime(),  nullable=True),
        sa.Column("expires_at",  sa.DateTime(),  nullable=False),
        sa.Column("accepted_at", sa.DateTime(),  nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_invites_tenant_id", "invites", ["tenant_id"])
    op.create_index("ix_invites_token_hash", "invites", ["token_hash"], unique=True)

    op.add_column("tenants", sa.Column("status", sa.String(20), server_default="active"))
    op.add_column("tenants", sa.Column("monthly_statement_quota", sa.Integer(), nullable=True))

    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("removed_at", sa.DateTime(), nullable=True))

    op.add_column("jobs", sa.Column("api_key_id", sa.String(36), nullable=True))
    op.add_column("usage", sa.Column("api_key_id", sa.String(36), nullable=True))
    op.create_index("ix_usage_created_at", "usage", ["created_at"])

    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.create_foreign_key("fk_jobs_api_key_id", "jobs", "api_keys",
                              ["api_key_id"], ["id"], ondelete="SET NULL")
        op.create_foreign_key("fk_usage_api_key_id", "usage", "api_keys",
                              ["api_key_id"], ["id"], ondelete="SET NULL")

    # every existing tenant gets exactly one owner: its earliest admin
    users = sa.table("users", sa.column("id"), sa.column("tenant_id"),
                     sa.column("role"), sa.column("created_at"))
    rows = bind.execute(sa.select(users.c.id, users.c.tenant_id, users.c.created_at)
                        .where(users.c.role == "admin")
                        .order_by(users.c.tenant_id, users.c.created_at)).fetchall()
    seen = set()
    for user_id, tenant_id, _created in rows:
        if tenant_id in seen:
            continue
        seen.add(tenant_id)
        bind.execute(users.update().where(users.c.id == user_id).values(role="owner"))


def downgrade() -> None:
    users = sa.table("users", sa.column("role"))
    op.get_bind().execute(users.update().where(users.c.role == "owner").values(role="admin"))
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.drop_constraint("fk_usage_api_key_id", "usage", type_="foreignkey")
        op.drop_constraint("fk_jobs_api_key_id", "jobs", type_="foreignkey")
    op.drop_index("ix_usage_created_at", table_name="usage")
    op.drop_column("usage", "api_key_id")
    op.drop_column("jobs", "api_key_id")
    for col in ("removed_at", "terms_accepted_at", "last_login_at"):
        op.drop_column("users", col)
    op.drop_column("tenants", "monthly_statement_quota")
    op.drop_column("tenants", "status")
    op.drop_index("ix_invites_token_hash", table_name="invites")
    op.drop_index("ix_invites_tenant_id", table_name="invites")
    op.drop_table("invites")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_table("api_keys")
