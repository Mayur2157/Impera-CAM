"""Who is calling: a portal user (Bearer JWT) or a customer system (X-API-Key).

Every /api/v1 route depends on one of the guards here, so role, scope and
suspension rules live in one place and are enforced on the server — the UI
hiding a control is never the only check.

    portal_user           any signed-in portal user (Bearer JWT only)
    jobs_caller(scope)    a portal user, or an API key holding ``scope``
    require_role(*roles)  a portal user with one of these roles
    require_superuser     Impera staff
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..config import settings
from ..db.base import get_db
from ..db.models import ApiKey, Tenant, User
from ..ratelimit import hit
from .auth import user_from_token

_bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

KEY_PREFIX = "icam_live_"
# last_used_at is written at most this often per key, not on every request
_TOUCH_EVERY = timedelta(minutes=1)


@dataclass
class Principal:
    user: User
    tenant: Tenant
    api_key: ApiKey | None = None

    @property
    def tenant_id(self) -> str:
        return self.tenant.id

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def is_superuser(self) -> bool:
        return bool(self.user.is_superuser)

    @property
    def suspended(self) -> bool:
        return self.tenant.status == "suspended"


def hash_key(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _unauthorized(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail,
                         headers={"WWW-Authenticate": "Bearer"})


def portal_user(token: str | None = Depends(_bearer), db: Session = Depends(get_db)) -> Principal:
    if not token:
        raise _unauthorized("Not authenticated")
    user = user_from_token(token, db)
    return Principal(user=user, tenant=user.tenant)


def _from_api_key(secret: str, scope: str, db: Session) -> Principal:
    key = db.query(ApiKey).filter(ApiKey.key_hash == hash_key(secret)).first()
    if key is None or key.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or revoked API key")
    tenant = db.query(Tenant).filter(Tenant.id == key.tenant_id).first()
    if tenant is None or tenant.status == "suspended":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "this organisation is suspended — its API keys are disabled")
    if scope not in (key.scopes or []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"this API key lacks the {scope} scope")
    hit("api_key", key.id, settings.api_key_per_minute, 60,
        message="API key rate limit reached — slow down and retry")

    now = datetime.utcnow()
    if key.last_used_at is None or now - key.last_used_at > _TOUCH_EVERY:
        key.last_used_at = now
        db.commit()
    # the job is filed under the person who created the key
    return Principal(user=key.creator, tenant=tenant, api_key=key)


def jobs_caller(scope: str):
    """A portal user, or a customer system whose key holds ``scope``."""
    def dependency(
        x_api_key: str | None = Header(None),
        token: str | None = Depends(_bearer),
        db: Session = Depends(get_db),
    ) -> Principal:
        if x_api_key:
            return _from_api_key(x_api_key.strip(), scope, db)
        return portal_user(token, db)
    return dependency


def require_role(*roles: str):
    def dependency(p: Principal = Depends(portal_user)) -> Principal:
        if p.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "you don't have permission to do that — ask an organisation admin")
        return p
    return dependency


def require_superuser(p: Principal = Depends(portal_user)) -> Principal:
    if not p.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Impera staff only")
    return p
