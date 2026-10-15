"""Auth, rate limits, secrets, the registry race and production guards."""
from __future__ import annotations

import dataclasses

import pytest

from conftest import register


def test_register_login_me(client):
    h = register(client, "Acme Lending")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["org_name"] == "Acme Lending" and me["role"] == "admin"
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limited(client, monkeypatch):
    from app.api import auth_routes

    monkeypatch.setattr(auth_routes, "settings",
                        dataclasses.replace(auth_routes.settings, login_per_minute=3))
    codes = [client.post("/api/auth/login",
                         data={"username": "nobody@example.com", "password": "wrong-pass"}
                         ).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_password_seal_roundtrip():
    from app.secretbox import seal, unseal

    token = seal("hunter2")
    assert token and "hunter2" not in token
    assert unseal(token) == "hunter2"
    assert seal(None) is None and unseal(None) is None


def test_registry_insert_race_becomes_update(monkeypatch):
    """Two workers both miss the row and insert: the loser must update, not fail."""
    from sqlalchemy.orm import Query

    from app.core import registry
    from app.db.base import SessionLocal
    from app.db.models import AccountRegistry, Tenant

    db = SessionLocal()
    db.add(Tenant(id="t1", name="T"))
    db.add(AccountRegistry(tenant_id="t1", account_number="123456",
                           customer_name="first", email="a@example.com"))
    db.commit()
    db.close()

    real_first = Query.first
    misses = [1]

    def first_misses_once(self):
        if misses and self.column_descriptions[0]["entity"] is AccountRegistry:
            misses.pop()
            return None                    # the other worker's row is not visible yet
        return real_first(self)

    monkeypatch.setattr(Query, "first", first_misses_once)
    registry.register({"account_number": "123456", "customer_name": "second",
                       "email": "b@example.com"}, tenant_id="t1")

    db = SessionLocal()
    rows = db.query(AccountRegistry).all()
    assert len(rows) == 1 and rows[0].customer_name == "second"
    db.close()


def test_production_guards():
    from app.config import production_problems, settings

    unsafe = dataclasses.replace(settings, jwt_secret="CHANGE-ME", allowed_origins=("*",),
                                 mysql_url="mysql+pymysql://root:x@db/impera_cam")
    assert len(production_problems(unsafe)) == 3

    safe = dataclasses.replace(settings, jwt_secret="s" * 48,
                               allowed_origins=("https://app.example.com",),
                               mysql_url="mysql+pymysql://impera:x@db/impera_cam")
    assert production_problems(safe) == []


def test_prod_start_refused_with_defaults(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main

    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, env="prod"))
    monkeypatch.setattr(main, "production_problems", lambda: ["placeholder secret"])
    with pytest.raises(RuntimeError, match="refusing to start"):
        with TestClient(main.app):
            pass
