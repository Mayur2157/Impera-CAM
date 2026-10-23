"""Usage against the plan — statements and pages processed, from the billing meter.

GET /api/v1/usage?from=YYYY-MM-DD&to=YYYY-MM-DD&group_by=day|user|api_key

One `usage` row is written per finished file (app/tasks.py), so these are
billable units, not HTTP requests. Jobs sent without an API key are "Portal".
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...auth.principal import Principal, portal_user
from ...db.base import get_db
from ...db.models import ApiKey, Usage, User

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])

MAX_DAYS = 366


def _totals(db: Session, tenant_id: str, start: datetime, end: datetime) -> dict:
    statements, pages = (db.query(func.coalesce(func.sum(Usage.statements), 0),
                                  func.coalesce(func.sum(Usage.pages), 0))
                         .filter(Usage.tenant_id == tenant_id,
                                 Usage.created_at >= start, Usage.created_at < end)
                         .one())
    return {"statements": int(statements), "pages": int(pages)}


@router.get("")
def usage(
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    group_by: Literal["day", "user", "api_key"] = "day",
    p: Principal = Depends(portal_user),
    db: Session = Depends(get_db),
):
    today = datetime.utcnow().date()
    to = to or today
    from_ = from_ or to - timedelta(days=29)
    if from_ > to:
        raise HTTPException(400, "'from' must be on or before 'to'")
    if (to - from_).days >= MAX_DAYS:
        raise HTTPException(400, f"choose a range of at most {MAX_DAYS} days")

    start = datetime.combine(from_, datetime.min.time())
    end = datetime.combine(to + timedelta(days=1), datetime.min.time())
    in_range = (Usage.tenant_id == p.tenant_id, Usage.created_at >= start, Usage.created_at < end)
    sums = (func.coalesce(func.sum(Usage.statements), 0), func.coalesce(func.sum(Usage.pages), 0))

    if group_by == "day":
        day = func.date(Usage.created_at)
        found = {str(d)[:10]: (s, pg) for d, s, pg in
                 db.query(day, *sums).filter(*in_range).group_by(day)}
        series = []
        for n in range((to - from_).days + 1):
            key = (from_ + timedelta(days=n)).isoformat()
            s, pg = found.get(key, (0, 0))
            series.append({"key": key, "label": key, "statements": int(s), "pages": int(pg)})
    elif group_by == "user":
        rows = (db.query(Usage.user_id, User.email, *sums)
                .join(User, User.id == Usage.user_id)
                .filter(*in_range).group_by(Usage.user_id, User.email))
        series = [{"key": uid, "label": email, "statements": int(s), "pages": int(pg)}
                  for uid, email, s, pg in rows]
    else:
        rows = (db.query(Usage.api_key_id, ApiKey.name, ApiKey.prefix, *sums)
                .outerjoin(ApiKey, ApiKey.id == Usage.api_key_id)
                .filter(*in_range).group_by(Usage.api_key_id, ApiKey.name, ApiKey.prefix))
        series = [{"key": kid or "portal",
                   "label": f"{name} ({prefix}…)" if kid else "Portal",
                   "statements": int(s), "pages": int(pg)}
                  for kid, name, prefix, s, pg in rows]
    if group_by != "day":
        series.sort(key=lambda r: -r["statements"])

    t = p.tenant
    month_start = datetime.combine(today.replace(day=1), datetime.min.time())
    return {
        "plan": {"name": t.plan, "max_files_per_job": t.max_files, "max_upload_mb": t.max_upload_mb,
                 "monthly_statement_quota": t.monthly_statement_quota},
        "totals": _totals(db, p.tenant_id, start, end),
        "month_to_date": _totals(db, p.tenant_id, month_start,
                                 datetime.combine(today + timedelta(days=1), datetime.min.time())),
        "series": series,
    }
