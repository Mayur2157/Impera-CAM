"""Pydantic schemas for auth endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    org_name: str

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


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    tenant_id: str
    role: str
    org_name: str

    model_config = {"from_attributes": True}
