"""Login tests against auth-service, using a temporary SQLite file."""

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "tests" / "tmp_auth.db"
LOG_DIR = ROOT / "tests" / "tmp_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + DB_PATH.as_posix()
os.environ["JWT_SECRET_KEY"] = "test-secret-not-for-production"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["LOG_DIR"] = str(LOG_DIR)
os.environ["LOKI_URL"] = ""
os.environ["SERVICE_NAME"] = "auth-service"

sys.path.insert(0, str(ROOT / "services" / "auth-service"))
sys.path.insert(0, str(ROOT / "services"))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

PASSWORD = "correct-password"


def _client():
    return TestClient(app)


def _register(client: TestClient, email: str, role: str = "customer"):
    return client.post("/auth/register", json={
        "email": email,
        "password": PASSWORD,
        "full_name": "Test User",
        "role": role,
    })


def _set_user(email: str, **columns):
    assignments = ", ".join(f"{name} = ?" for name in columns)
    with sqlite3.connect(DB_PATH, timeout=5) as conn:
        conn.execute(
            f"UPDATE users SET {assignments} WHERE email = ?",
            [*columns.values(), email],
        )


def test_login_success_returns_token_and_role():
    with _client() as client:
        created = _register(client, "login-ok@example.com")
        assert created.status_code == 201

        response = client.post("/auth/login", json={
            "email": "login-ok@example.com",
            "password": PASSWORD,
        })
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["role"] == "customer"
        assert body["access_token"]
        assert body["user_id"]


def test_login_wrong_password():
    with _client() as client:
        assert _register(client, "login-bad@example.com").status_code == 201
        response = client.post("/auth/login", json={
            "email": "login-bad@example.com",
            "password": "not-the-password",
        })
        assert response.status_code == 401


def test_login_unknown_email():
    with _client() as client:
        response = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": PASSWORD,
        })
        assert response.status_code == 401


def test_login_disabled_account():
    email = "login-disabled@example.com"
    with _client() as client:
        assert _register(client, email).status_code == 201
        _set_user(email, is_active=0)
        response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 403


def test_public_register_cannot_choose_admin_or_manufacturer():
    with _client() as client:
        admin = _register(client, "self-admin@example.com", role="admin")
        assert admin.status_code == 403
        manufacturer = _register(client, "self-mfg@example.com", role="manufacturer")
        assert manufacturer.status_code == 403


def test_admin_can_create_manufacturer_and_customer_cannot():
    email = "promoted-admin@example.com"
    with _client() as client:
        assert _register(client, email).status_code == 201
        customer = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()
        denied = client.post(
            "/auth/manufacturers",
            headers={"Authorization": f"Bearer {customer['access_token']}"},
            json={
                "email": "mfg@example.com",
                "password": PASSWORD,
                "full_name": "Acme",
                "wallet_address": "0x1111111111111111111111111111111111111111",
            },
        )
        assert denied.status_code == 403

        _set_user(email, role="admin")
        admin = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()
        created = client.post(
            "/auth/manufacturers",
            headers={"Authorization": f"Bearer {admin['access_token']}"},
            json={
                "email": "mfg@example.com",
                "password": PASSWORD,
                "full_name": "Acme",
                "wallet_address": "0x1111111111111111111111111111111111111111",
            },
        )
        assert created.status_code == 201
        assert created.json()["role"] == "manufacturer"

        logged_in = client.post("/auth/login", json={
            "email": "mfg@example.com",
            "password": PASSWORD,
        })
        assert logged_in.status_code == 200
        assert logged_in.json()["role"] == "manufacturer"
