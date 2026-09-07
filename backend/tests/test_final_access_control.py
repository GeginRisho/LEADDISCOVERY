import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import Organization, User

client = TestClient(app)

def get_admin_headers():
    res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if res.status_code == 200:
        return {"Authorization": f"Bearer {res.json()['access_token']}"}
    
    # Fallback registration if missing
    client.post("/api/auth/register", json={"email": "admin_access_test@example.com", "password": "adminpass123"})
    db = SessionLocal()
    u = db.query(User).filter(User.email == "admin_access_test@example.com").first()
    if u:
        u.role = "ADMIN"
        db.commit()
    db.close()
    login_res = client.post("/api/auth/login", json={"email": "admin_access_test@example.com", "password": "adminpass123"})
    return {"Authorization": f"Bearer {login_res.json()['access_token']}"}

def get_user_headers():
    res = client.post("/api/auth/login", json={"email": "testuser@leaddiscovery.com", "password": "User@12345"})
    if res.status_code == 200:
        return {"Authorization": f"Bearer {res.json()['access_token']}"}
    
    client.post("/api/auth/register", json={"email": "normal_user_test@example.com", "password": "userpass123"})
    login_res = client.post("/api/auth/login", json={"email": "normal_user_test@example.com", "password": "userpass123"})
    return {"Authorization": f"Bearer {login_res.json()['access_token']}"}

def test_1_normal_user_get_organizations_returns_403():
    user_headers = get_user_headers()
    res = client.get("/api/organizations", headers=user_headers)
    assert res.status_code == 403, f"Expected 403 Forbidden for normal user, got {res.status_code}: {res.text}"

def test_2_admin_user_get_organizations_returns_200():
    admin_headers = get_admin_headers()
    res = client.get("/api/organizations", headers=admin_headers)
    assert res.status_code == 200, f"Expected 200 OK for admin user, got {res.status_code}: {res.text}"
    assert "organizations" in res.json()

def test_3_normal_user_create_organization_returns_403():
    user_headers = get_user_headers()
    payload = {
        "name": "Unauthorized Test Org",
        "category": "Education",
        "district": "Chennai"
    }
    res = client.post("/api/organizations/manual", json=payload, headers=user_headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"

def test_4_normal_user_verify_organization_returns_403():
    user_headers = get_user_headers()
    res = client.post("/api/organizations/999999/verify", headers=user_headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"

def test_5_admin_user_create_organization_returns_201():
    admin_headers = get_admin_headers()
    payload = {
        "name": "Access Control Test Org Admin",
        "category": "Technology",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "state": "Tamil Nadu",
        "country": "India"
    }
    res = client.post("/api/organizations/manual", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.text}"
    org_id = res.json()["id"]

    # Cleanup
    client.delete(f"/api/organizations/{org_id}", headers=admin_headers)

def test_6_admin_user_verify_organization_returns_200():
    admin_headers = get_admin_headers()
    # Create org first
    payload = {
        "name": "Access Control Verify Target Org",
        "category": "Healthcare",
        "district": "Madurai",
        "city": "Madurai",
        "state": "Tamil Nadu",
        "country": "India"
    }
    create_res = client.post("/api/organizations/manual", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    org_id = create_res.json()["id"]

    try:
        verify_res = client.post(f"/api/organizations/{org_id}/verify", headers=admin_headers)
        assert verify_res.status_code == 200
        assert verify_res.json()["admin_verified"] is True
    finally:
        client.delete(f"/api/organizations/{org_id}", headers=admin_headers)

def test_7_normal_user_fast_search_returns_200():
    user_headers = get_user_headers()
    res = client.get("/api/search/fast?category=college&location=Chennai", headers=user_headers)
    assert res.status_code == 200, f"Fast search failed for regular user: {res.status_code}"
    data = res.json()
    assert "results" in data or "organizations" in data or "total" in data

def test_8_admin_verified_org_appears_first_in_fast_search():
    admin_headers = get_admin_headers()
    
    # 1. Create Admin Verified Org in Puducherry
    org_admin = client.post("/api/organizations/manual", json={
        "name": "Alpha Priority Hotel Puducherry",
        "category": "Hotel",
        "district": "Puducherry",
        "city": "Puducherry",
        "state": "Puducherry UT",
        "country": "India",
        "website": "https://alphaprioritypuducherryhotel.com"
    }, headers=admin_headers).json()
    org_admin_id = org_admin["id"]
    client.post(f"/api/organizations/{org_admin_id}/verify", headers=admin_headers)

    # 2. Create Scraper Verified Org in Puducherry
    db = SessionLocal()
    org_scraper = Organization(
        name="Beta Scraper Hotel Puducherry",
        category="Hotel",
        district="Puducherry",
        city="Puducherry",
        state="Puducherry UT",
        country="India",
        admin_verified=False,
        source_type="SCRAPER_VERIFIED",
        confidence="HIGH"
    )
    db.add(org_scraper)
    db.commit()
    db.refresh(org_scraper)
    org_scraper_id = org_scraper.id
    db.close()

    try:
        # Search for Hotel + Puducherry
        res = client.get("/api/search/fast?category=Hotel&location=Puducherry")
        assert res.status_code == 200
        results = res.json().get("results", [])
        
        # Verify both appear and Alpha Priority (admin verified) appears before Beta Scraper
        names = [r.get("name") for r in results]
        assert "Alpha Priority Hotel Puducherry" in names
        assert "Beta Scraper Hotel Puducherry" in names
        assert names.index("Alpha Priority Hotel Puducherry") < names.index("Beta Scraper Hotel Puducherry")
    finally:
        client.delete(f"/api/organizations/{org_admin_id}", headers=admin_headers)
        db_clean = SessionLocal()
        o = db_clean.query(Organization).filter(Organization.id == org_scraper_id).first()
        if o:
            db_clean.delete(o)
            db_clean.commit()
        db_clean.close()

def test_9_wrong_location_admin_verified_org_excluded():
    admin_headers = get_admin_headers()
    
    # Admin verified org in Chennai
    org_chennai = client.post("/api/organizations/manual", json={
        "name": "Gamma Admin Hotel Chennai",
        "category": "Hotel",
        "district": "Chennai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "India",
        "website": "https://gammachennaihotel.com"
    }, headers=admin_headers).json()
    org_chennai_id = org_chennai["id"]
    client.post(f"/api/organizations/{org_chennai_id}/verify", headers=admin_headers)

    try:
        # Search for Hotel + Puducherry
        res = client.get("/api/search/fast?category=Hotel&location=Puducherry")
        assert res.status_code == 200
        results = res.json().get("results", [])
        names = [r.get("name") for r in results]
        assert "Gamma Admin Hotel Chennai" not in names, "Wrong location admin verified org must NOT bypass location filter!"
    finally:
        client.delete(f"/api/organizations/{org_chennai_id}", headers=admin_headers)
