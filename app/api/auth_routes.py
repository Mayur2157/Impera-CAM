"""Authentication endpoints.

POST /api/auth/register  — create tenant + owner user (terms accepted), return JWT
POST /api/auth/login     — OAuth2 password form, return JWT
GET  /api/auth/me        — current user info
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth.auth import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..auth.schemas import RegisterIn, TokenOut, UserOut
from ..config import settings
from ..db.base import get_db
from ..db.models import Tenant, User
from ..ratelimit import limit

router = APIRouter(prefix="/api/auth", tags=["auth"])

_register_limit = limit("register", lambda: settings.register_per_hour, 3600)
_login_limit = limit("login", lambda: settings.login_per_minute, 60)


@router.post("/register", response_model=TokenOut, status_code=201,
             dependencies=[Depends(_register_limit)])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")

    tenant = Tenant(name=body.org_name)
    db.add(tenant)
    db.flush()          # get tenant.id before committing

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        tenant_id=tenant.id,
        role="owner",
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenOut(access_token=create_token(user.id))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(_login_limit)])
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == form.username,
        User.is_active.is_(True),
    ).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.utcnow()
    db.commit()
    return TokenOut(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return UserOut(
        id=current.id,
        email=current.email,
        tenant_id=current.tenant_id,
        role=current.role,
        is_superuser=bool(current.is_superuser),
        org_name=current.tenant.name,
        org_status=current.tenant.status or "active",
        plan=current.tenant.plan or "free",
    )
