"""SaaS scale-out — per-file queue bookkeeping, billing rows that outlive jobs.

* file_tasks.position     upload order (was implicit, and ordered by uuid)
* file_tasks.started_at / finished_at   for the stuck-task reaper and timings
* index on file_tasks.status            tenant active-file cap, reaper
* usage.job_id ON DELETE SET NULL        purging a job keeps its usage rows

Revision ID: 002
Revises: 001
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def _usage_job_fk(bind):
    for fk in sa.inspect(bind).get_foreign_keys("usage"):
        if fk.get("referred_table") == "jobs":
            return fk.get("name")
    return None


def upgrade() -> None:
    op.add_column("file_tasks", sa.Column("position", sa.Integer(), server_default="0"))
    op.add_column("file_tasks", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("file_tasks", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.create_index("ix_file_tasks_status", "file_tasks", ["status"])

    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # 001 left this FK unnamed, so MySQL generated the name: look it up
        name = _usage_job_fk(bind)
        if name:
            op.drop_constraint(name, "usage", type_="foreignkey")
        op.create_foreign_key("fk_usage_job_id", "usage", "jobs",
                              ["job_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.drop_constraint("fk_usage_job_id", "usage", type_="foreignkey")
        op.create_foreign_key(None, "usage", "jobs", ["job_id"], ["id"])
    op.drop_index("ix_file_tasks_status", table_name="file_tasks")
    op.drop_column("file_tasks", "finished_at")
    op.drop_column("file_tasks", "started_at")
    op.drop_column("file_tasks", "position")
