"""JWT + bcrypt authentication helpers.

Tokens are HS256 JWTs signed with BSX_JWT_SECRET.  They carry the user's id
as the 'sub' claim and expire after BSX_JWT_EXPIRE_HOURS hours (default 24).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import settings
from ..db.base import get_db
from ..db.models import User

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# Request dependency
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency.  Raises 401 for any invalid or expired token."""
    return user_from_token(token, db)


def user_from_token(token: str, db: Session) -> User:
    """The active user a token names. Raises 401 for any invalid or expired token."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = (
        db.query(User)
        .filter(User.id == user_id, User.is_active.is_(True))
        .first()
    )
    if not user:
        raise cred_exc
    return user
