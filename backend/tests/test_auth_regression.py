import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.models.models import User
from app.core.security import verify_password, get_password_hash
from app.api.auth import seed_default_users

client = TestClient(app)

def test_auth_regression_plain_password_bcrypt_verification():
    """
    Regression Test 1: Verify native bcrypt implementation.
    Proves bcrypt receives plaintext password, normal short passwords work,
    and invalid/corrupt hashes return False safely without ValueError.
    """
    password = "admin123"
    hashed = get_password_hash(password)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False
    assert verify_password("admin123", "invalid_corrupt_hash") is False
    assert verify_password("admin123", "$2b$12$" + "x" * 70) is False

def test_auth_regression_seeded_admin_login():
    """
    Regression Test 2: Verify login with admin@leaddiscovery.com and admin123 via JSON & Form endpoints.
    """
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()

    # JSON Login
    res_json = client.post("/api/auth/login", json={
        "email": "admin@leaddiscovery.com",
        "password": "admin123"
    })
    assert res_json.status_code == 200, f"JSON login failed: {res_json.text}"
    json_data = res_json.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"

    # Form Login
    res_form = client.post("/api/auth/login-form", data={
        "username": "admin@leaddiscovery.com",
        "password": "admin123"
    })
    assert res_form.status_code == 200, f"Form login failed: {res_form.text}"
    form_data = res_form.json()
    assert "access_token" in form_data

def test_auth_regression_incorrect_password_returns_error():
    """
    Regression Test 3: Verify incorrect password returns HTTP 400 error.
    """
    res = client.post("/api/auth/login", json={
        "email": "admin@leaddiscovery.com",
        "password": "WrongPassword999!"
    })
    assert res.status_code == 400
    assert "Incorrect email or password" in res.json()["detail"]

def test_auth_regression_cors_allowed_origins():
    """
    Regression Test 4: Verify CORS allows https://leaddiscovery.vercel.app.
    """
    res = client.options("/api/auth/login", headers={
        "Origin": "https://leaddiscovery.vercel.app",
        "Access-Control-Request-Method": "POST"
    })
    assert res.status_code in [200, 204]
    assert res.headers.get("access-control-allow-origin") == "https://leaddiscovery.vercel.app"
