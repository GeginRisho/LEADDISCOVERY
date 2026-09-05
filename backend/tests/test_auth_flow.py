import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import SessionLocal, get_db
from app.models.models import User
from app.core.security import verify_password, get_password_hash
from app.api.auth import seed_default_users

client = TestClient(app)

def test_auth_comprehensive_flow():
    db = SessionLocal()
    seed_default_users(db)

    # 1. Test Admin login
    res_admin = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    assert res_admin.status_code == 200
    token_admin = res_admin.json()["access_token"]
    assert token_admin

    # Verify admin /me
    res_admin_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_admin_me.status_code == 200
    assert res_admin_me.json()["email"] == "admin@leaddiscovery.com"
    assert res_admin_me.json()["role"] == "ADMIN"

    # 2. Test Normal User login with correct password
    res_user = client.post("/api/auth/login", json={"email": "testuser@leaddiscovery.com", "password": "User@12345"})
    assert res_user.status_code == 200
    token_user = res_user.json()["access_token"]
    assert token_user

    # Verify user /me
    res_user_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_user}"})
    assert res_user_me.status_code == 200
    assert res_user_me.json()["email"] == "testuser@leaddiscovery.com"
    assert res_user_me.json()["role"] == "USER"

    # 3. Test Email Case-Insensitive Normalization
    res_case = client.post("/api/auth/login", json={"email": "  TESTUSER@LEADDISCOVERY.COM  ", "password": "User@12345"})
    assert res_case.status_code == 200

    # 4. Test Wrong Password
    res_wrong = client.post("/api/auth/login", json={"email": "testuser@leaddiscovery.com", "password": "WrongPassword123"})
    assert res_wrong.status_code == 400
    assert res_wrong.json()["detail"] == "Incorrect email or password."

    # 5. Test Duplicate Registration Rejection
    res_dup = client.post("/api/auth/register", json={"email": "testuser@leaddiscovery.com", "password": "User@12345"})
    assert res_dup.status_code == 400
    assert "already registered" in res_dup.json()["detail"].lower() or "already exists" in res_dup.json()["detail"].lower()

    # 6. Test New User Registration
    new_email = "auth-test@example.com"
    # Clean up existing test email if present
    db.query(User).filter(User.email == new_email).delete()
    db.commit()

    res_reg = client.post("/api/auth/register", json={"email": new_email, "password": "TestUser@12345"})
    assert res_reg.status_code == 201
    assert res_reg.json()["email"] == new_email

    # Test login with new user
    res_new_login = client.post("/api/auth/login", json={"email": new_email, "password": "TestUser@12345"})
    assert res_new_login.status_code == 200
    db.close()

    # Clean up temporary test accounts
    db_clean = SessionLocal()
    db_clean.query(User).filter(User.email == new_email).delete()
    db_clean.commit()
    db_clean.close()

def test_suspended_user_rejection():
    suspended_email = "suspended-user-test@example.com"
    db = SessionLocal()
    
    # 1. Clean up & Create suspended user in DB directly
    db.query(User).filter(func.lower(User.email) == suspended_email).delete()
    db.commit()

    susp_user = User(
        email=suspended_email,
        hashed_password=get_password_hash("Password123!"),
        role="USER",
        status="SUSPENDED"
    )
    db.add(susp_user)
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        res_susp = client.post("/api/auth/login", json={"email": suspended_email, "password": "Password123!"})
        assert res_susp.status_code == 403
        assert "suspended" in res_susp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
        db.query(User).filter(func.lower(User.email) == suspended_email).delete()
        db.commit()
        db.close()
