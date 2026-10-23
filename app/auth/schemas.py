"""Pydantic schemas for auth endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    org_name: str
    # DPDP: consent is an explicit, unticked-by-default choice at signup
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def pw_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("org_name")
    @classmethod
    def org_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("org_name is required")
        return v

    @field_validator("accept_terms")
    @classmethod
    def terms_accepted(cls, v: bool) -> bool:
        if not v:
            raise ValueError("accept the terms and privacy notice to create an account")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    tenant_id: str
    role: str                 # owner | admin | member
    is_superuser: bool
    org_name: str
    org_status: str           # active | suspended
    plan: str

    model_config = {"from_attributes": True}
