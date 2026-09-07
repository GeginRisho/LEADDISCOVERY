import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.models.models import Organization, User

client = TestClient(app)

def get_admin_headers():
    res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if res.status_code == 200:
        return {"Authorization": f"Bearer {res.json()['access_token']}"}, "admin@leaddiscovery.com"
    
    reg_resp = client.post("/api/auth/register", json={
        "email": "admin_priority_test@example.com",
        "password": "adminpass123",
        "role": "ADMIN"
    })
    login_resp = client.post("/api/auth/login", json={"email": "admin_priority_test@example.com", "password": "adminpass123"})
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}, "admin_priority_test@example.com"

def test_admin_verification_persistence_and_provenance():
    headers, admin_email = get_admin_headers()

    # Create an initial organization via Admin API
    payload = {
        "name": "Puducherry Heritage Hotel",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "address": "12 Heritage Street"
    }
    create_res = client.post("/api/admin/organizations", json=payload, headers=headers)
    assert create_res.status_code in (200, 201), create_res.text
    org_data = create_res.json()
    org_id = org_data["id"]

    try:
        # 1. Unverify first to simulate a SCRAPER_VERIFIED / MANUAL org
        un_init = client.post(f"/api/organizations/{org_id}/unverify", headers=headers)
        assert un_init.status_code == 200

        # 2. Verify via API
        res = client.post(f"/api/organizations/{org_id}/verify", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["admin_verified"] is True
        assert data["source_type"] == "ADMIN_VERIFIED"
        assert data["verified_by"] == admin_email

        # 3. Unverify via API (Must restore provenance!)
        res_un = client.post(f"/api/organizations/{org_id}/unverify", headers=headers)
        assert res_un.status_code == 200, res_un.text
        data_un = res_un.json()
        assert data_un["admin_verified"] is False
        assert data_un["source_type"] != "ADMIN_VERIFIED"
    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)

def test_admin_verified_priority_ranking_and_location_scoping():
    headers, _ = get_admin_headers()

    # Create Hotel A: Puducherry (Admin Verified)
    hotel_a_payload = {
        "name": "Hotel A - Admin Verified",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "website_url": "https://hotel-a-puducherry.com"
    }
    res_a = client.post("/api/admin/organizations", json=hotel_a_payload, headers=headers)
    assert res_a.status_code in (200, 201)
    id_a = res_a.json()["id"]

    # Create Hotel B: Puducherry (Unverified / Scraper Verified)
    hotel_b_payload = {
        "name": "Hotel B - Scraper Verified",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "website_url": "https://hotel-b-puducherry.com"
    }
    res_b = client.post("/api/admin/organizations", json=hotel_b_payload, headers=headers)
    assert res_b.status_code in (200, 201)
    id_b = res_b.json()["id"]
    client.post(f"/api/organizations/{id_b}/unverify", headers=headers)

    # Create Hotel C: Chennai (Admin Verified - Different location!)
    hotel_c_payload = {
        "name": "Hotel C - Chennai Admin Verified",
        "category": "hotel",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "website_url": "https://hotel-c-chennai.com"
    }
    res_c = client.post("/api/admin/organizations", json=hotel_c_payload, headers=headers)
    assert res_c.status_code in (200, 201)
    id_c = res_c.json()["id"]

    try:
        # Search for "hotel" + "puducherry"
        res = client.get("/api/search/fast?category=hotel&location=puducherry")
        assert res.status_code == 200, res.text
        payload = res.json()
        results = [r for r in payload["results"] if r.get("id") in (id_a, id_b, id_c) or r.get("organization_id") in (id_a, id_b, id_c)]
        
        # CRITICAL REQUIREMENT #1:
        # 1. Hotel A (Puducherry Admin Verified) MUST be first!
        # 2. Hotel B (Puducherry Scraper Verified) MUST be second!
        # 3. Hotel C (Chennai Admin Verified) MUST NOT appear in Puducherry results!
        assert len(results) >= 1
        assert results[0]["name"] == "Hotel A - Admin Verified"
        assert results[0]["admin_verified"] is True

        names = [r["name"] for r in results]
        assert "Hotel C - Chennai Admin Verified" not in names
    finally:
        client.delete(f"/api/admin/organizations/{id_a}", headers=headers)
        client.delete(f"/api/admin/organizations/{id_b}", headers=headers)
        client.delete(f"/api/admin/organizations/{id_c}", headers=headers)

def test_quarantined_organization_exclusion():
    headers, _ = get_admin_headers()
    payload = {
        "name": "Fake Hotel Portal",
        "category": "hotel",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry"
    }
    res = client.post("/api/admin/organizations", json=payload, headers=headers)
    assert res.status_code in (200, 201)
    org_id = res.json()["id"]

    try:
        # Quarantine the record
        update_payload = {
            "name": "Fake Hotel Portal",
            "is_quarantined": True,
            "quarantine_reason": "Directory listicle site"
        }
        client.put(f"/api/admin/organizations/{org_id}", json=update_payload, headers=headers)

        res_search = client.get("/api/search/fast?category=hotel&location=puducherry")
        assert res_search.status_code == 200
        names = [r["name"] for r in res_search.json()["results"]]
        assert "Fake Hotel Portal" not in names
    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)
