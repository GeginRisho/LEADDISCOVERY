import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.models.models import Organization, User, ScrapingTask

client = TestClient(app)

def get_admin_auth():
    res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if res.status_code == 200:
        return {"Authorization": f"Bearer {res.json()['access_token']}"}, "admin@leaddiscovery.com"
    
    reg_resp = client.post("/api/auth/register", json={
        "email": "final_admin@example.com",
        "password": "adminpass123",
        "role": "ADMIN"
    })
    login_resp = client.post("/api/auth/login", json={"email": "final_admin@example.com", "password": "adminpass123"})
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}, "final_admin@example.com"

def get_normal_user_auth():
    reg_resp = client.post("/api/auth/register", json={
        "email": "normaluser_final@example.com",
        "password": "userpass123",
        "role": "USER"
    })
    login_resp = client.post("/api/auth/login", json={"email": "normaluser_final@example.com", "password": "userpass123"})
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

def test_admin_create_organization_custom_category():
    """1. Admin can create organization with custom category."""
    headers, _ = get_admin_auth()
    payload = {
        "name": "Puducherry Botanical Research Institute",
        "category": "botanical_research",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "official_website_url": "https://puducherrybotanical.org"
    }
    res = client.post("/api/admin/organizations", json=payload, headers=headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()
    org_id = data["id"]
    assert data["category"] == "BOTANICAL_RESEARCH" or data["category"] == "botanical_research"
    client.delete(f"/api/admin/organizations/{org_id}", headers=headers)

def test_admin_edit_organization():
    """2. Admin can edit organization."""
    headers, _ = get_admin_auth()
    create_payload = {
        "name": "Edit Test Org",
        "category": "clinic",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "city": "Coimbatore"
    }
    create_res = client.post("/api/admin/organizations", json=create_payload, headers=headers)
    org_id = create_res.json()["id"]

    try:
        update_payload = {
            "name": "Edit Test Org Updated",
            "display_name": "Updated Clinic",
            "city": "Coimbatore City"
        }
        update_res = client.put(f"/api/admin/organizations/{org_id}", json=update_payload, headers=headers)
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Edit Test Org Updated"
        assert update_res.json()["display_name"] == "Updated Clinic"
    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)

def test_admin_verify_and_unverify_provenance_preservation():
    """3, 4, 5. Admin verify/unverify and provenance preservation."""
    headers, admin_email = get_admin_auth()
    payload = {
        "name": "Provenance Test NGO",
        "category": "ngo",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry"
    }
    create_res = client.post("/api/admin/organizations", json=payload, headers=headers)
    org_id = create_res.json()["id"]

    try:
        # Unverify first to set non-admin_verified state with ADMIN_ADDED provenance
        client.post(f"/api/organizations/{org_id}/unverify", headers=headers)

        # 1. Verify
        v_res = client.post(f"/api/organizations/{org_id}/verify", headers=headers)
        assert v_res.status_code == 200
        assert v_res.json()["admin_verified"] is True
        assert v_res.json()["source_type"] == "ADMIN_VERIFIED"
        assert v_res.json()["verified_by"] == admin_email

        # 2. Unverify - must preserve ADMIN_ADDED / original provenance
        u_res = client.post(f"/api/organizations/{org_id}/unverify", headers=headers)
        assert u_res.status_code == 200
        assert u_res.json()["admin_verified"] is False
        assert u_res.json()["source_type"] != "ADMIN_VERIFIED"
    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)

def test_normal_user_authorization_blocked():
    """6, 7. Normal user cannot verify or create admin organization (403)."""
    admin_headers, _ = get_admin_auth()
    user_headers = get_normal_user_auth()

    # Create dummy org via Admin
    create_res = client.post("/api/admin/organizations", json={
        "name": "Auth Block Test Org",
        "category": "bank",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Salem",
        "city": "Salem"
    }, headers=admin_headers)
    org_id = create_res.json()["id"]

    try:
        # User trying admin endpoints gets 403 Forbidden
        u_create = client.post("/api/admin/organizations", json={"name": "Fake User Org", "category": "bank", "district": "Salem"}, headers=user_headers)
        assert u_create.status_code == 403

        u_verify = client.post(f"/api/organizations/{org_id}/verify", headers=user_headers)
        assert u_verify.status_code == 403
    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=admin_headers)

def test_fast_search_ranking_and_scoping():
    """8, 9, 10, 11, 13. Fast search ranking priority and scoping."""
    headers, _ = get_admin_auth()

    # 1. Puducherry Hotel - Admin Verified
    h_a = client.post("/api/admin/organizations", json={
        "name": "Fast Hotel A - Admin Verified",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry"
    }, headers=headers).json()["id"]

    # 2. Puducherry Hotel - Unverified
    h_b = client.post("/api/admin/organizations", json={
        "name": "Fast Hotel B - Unverified",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry"
    }, headers=headers).json()["id"]
    client.post(f"/api/organizations/{h_b}/unverify", headers=headers)

    # 3. Chennai Hotel - Admin Verified (Wrong location!)
    h_c = client.post("/api/admin/organizations", json={
        "name": "Fast Hotel C - Chennai Admin",
        "category": "hotel",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai"
    }, headers=headers).json()["id"]

    # 4. Puducherry Quarantined Hotel
    h_q = client.post("/api/admin/organizations", json={
        "name": "Fast Hotel Quarantined",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "is_quarantined": True,
        "quarantine_reason": "Portal"
    }, headers=headers).json()["id"]

    try:
        # Search hotel + puducherry
        res = client.get("/api/search/fast?category=hotel&location=puducherry")
        assert res.status_code == 200
        data = res.json()["results"]
        matching = [r for r in data if r.get("id") in (h_a, h_b, h_c, h_q)]

        # h_a MUST be first
        assert len(matching) >= 1
        assert matching[0]["name"] == "Fast Hotel A - Admin Verified"

        # h_c (Chennai) and h_q (Quarantined) MUST NOT appear in Puducherry results
        names = [r["name"] for r in data]
        assert "Fast Hotel C - Chennai Admin" not in names
        assert "Fast Hotel Quarantined" not in names
    finally:
        for org_id in (h_a, h_b, h_c, h_q):
            client.delete(f"/api/admin/organizations/{org_id}", headers=headers)

def test_branch_location_isolation():
    """12. Branch location matching works independently."""
    headers, _ = get_admin_auth()
    org_res = client.post("/api/admin/organizations", json={
        "name": "Multi Branch NGO HQ",
        "category": "ngo",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "branches": [
            {
                "branch_name": "Puducherry Regional NGO Branch",
                "country": "India",
                "state": "Puducherry UT",
                "district": "Puducherry",
                "city": "Puducherry"
            }
        ]
    }, headers=headers)
    org_id = org_res.json()["id"]

    try:
        res_pud = client.get("/api/search/fast?category=ngo&location=puducherry")
        assert res_pud.status_code == 200
        pud_matches = [r for r in res_pud.json()["results"] if r.get("id") == org_id or r.get("organization_id") == org_id]
        assert len(pud_matches) == 1
        assert pud_matches[0]["branch_name"] == "Puducherry Regional NGO Branch"
    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)

def test_ssrf_protection_remains_active():
    """20. SSRF protections block private IP addresses."""
    headers, _ = get_admin_auth()
    ssrf_payload = {
        "name": "SSRF Test Org",
        "category": "bank",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "official_website_url": "http://127.0.0.1/admin"
    }
    res = client.post("/api/admin/organizations", json=ssrf_payload, headers=headers)
    assert res.status_code == 400
    assert "ssrf" in res.json()["detail"].lower() or "internal" in res.json()["detail"].lower() or "blocked" in res.json()["detail"].lower()

def test_system_health_removed_from_frontend_navigation():
    """16, 17. System health removed from frontend navigation."""
    layout_path = os.path.join("frontend", "src", "components", "AppLayout.tsx")
    assert os.path.exists(layout_path)
    with open(layout_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "/admin/health" not in content
