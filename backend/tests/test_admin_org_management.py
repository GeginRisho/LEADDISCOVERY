import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import Organization, OrgBranch

client = TestClient(app)

def get_admin_headers():
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@leaddiscovery.com", "password": "admin123"}
    )
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_admin_org_create_and_validation():
    """
    Test 1: Admin Organization Creation with validation.
    - Valid creation returns 201 Created with admin_verified=True, source_type='ADMIN_VERIFIED', verification_method='ADMIN'.
    - official_website_verified remains independently tracked (not auto-forced true).
    - Invalid location combination (e.g. state=Puducherry UT + district=Erode) returns 400.
    """
    headers = get_admin_headers()

    # 1. Invalid Location Combo
    invalid_payload = {
        "name": "TEST INVALID ORG",
        "category": "HOSPITAL",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Erode", # Invalid combo!
        "city": "Erode"
    }
    res_inv = client.post("/api/admin/organizations", json=invalid_payload, headers=headers)
    assert res_inv.status_code == 400
    assert "invalid location combination" in res_inv.json()["detail"].lower()

    # 2. Valid Admin Creation
    valid_payload = {
        "name": "TEST PUDUCHERRY MULTISPECIALTY HOSPITAL",
        "display_name": "Test Puducherry Hospital",
        "category": "HOSPITAL",
        "sub_category": "MULTISPECIALTY",
        "description": "Leading hospital in Puducherry district.",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "address": "100 Beach Road",
        "pincode": "605001",
        "website_url": "https://testpuducherryhospital.com",
        "google_maps_url": "https://maps.google.com/?q=test+puducherry+hospital",
        "facebook_url": "https://facebook.com/testpuducherryhospital",
        "phone_numbers": [
            {"raw_value": "0413-2223344", "type": "MAIN"},
            {"raw_value": "9876543210", "type": "EMERGENCY"}
        ],
        "email_addresses": ["info@testpuducherryhospital.com", "contact@testpuducherryhospital.com"],
        "other_links": [{"label": "Patient Portal", "url": "https://testpuducherryhospital.com/portal", "link_type": "PORTAL"}]
    }

    res = client.post("/api/admin/organizations", json=valid_payload, headers=headers)
    assert res.status_code in (200, 201), res.text
    data = res.json()
    org_id = data["id"]

    assert data["name"] == "TEST PUDUCHERRY MULTISPECIALTY HOSPITAL"
    assert data["admin_verified"] is True
    assert data["source_type"] == "ADMIN_VERIFIED"
    assert data["verification_method"] == "ADMIN"
    # Verification method ADMIN, while official_website_verified remains independently tracked
    assert data["official_website_verified"] is False or data["official_website_verified"] is None

    # Cleanup org after checking
    db = SessionLocal()
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org:
        db.delete(org)
        db.commit()
    db.close()


def test_admin_created_record_immediate_fast_search():
    """
    Test 2: Prove Admin-created records are immediately searchable in Fast Search without waiting for scraper.
    """
    headers = get_admin_headers()
    org_payload = {
        "name": "TEST INSTANT ADMIN SCHOOL",
        "display_name": "Instant Admin CBSE School",
        "category": "SCHOOL",
        "sub_category": "CBSE",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Erode",
        "city": "Erode",
        "address": "123 Main Street",
        "pincode": "638001",
        "website_url": "https://instantadminschool.edu.in",
        "phone_numbers": [{"raw_value": "0424-9998877", "type": "MAIN"}]
    }

    res_create = client.post("/api/admin/organizations", json=org_payload, headers=headers)
    assert res_create.status_code in (200, 201)
    org_id = res_create.json()["id"]

    try:
        # Search via Fast Search endpoint immediately
        res_search = client.get("/api/search/fast?category=cbse+school&location=Erode&limit=20")
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["status"] == "SUCCESS"

        results = search_data["results"]
        matching_results = [r for r in results if r["name"] == "TEST INSTANT ADMIN SCHOOL" or r["id"] == org_id]

        assert len(matching_results) == 1, "Admin-created record should be immediately returned in Fast Search"
        item = matching_results[0]
        assert item["admin_verified"] is True
        assert item.get("verification_badge") == "ADMIN VERIFIED" or item.get("provenance_badge") == "ADMIN VERIFIED"
        assert item["district"] == "Erode"

    finally:
        # Cleanup
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)


def test_branch_location_isolation_and_matching():
    """
    Test 3: Branch isolation and location matching.
    Organization HQ: Chennai (Tamil Nadu)
    Branch 1: Puducherry (Puducherry district)
    Branch 2: Karaikal (Karaikal district)

    Search hospital + Puducherry -> Returns Branch 1 match only.
    Search hospital + Karaikal -> Returns Branch 2 match only.
    Search hospital + Erode -> Neither branch nor HQ qualifies.
    """
    headers = get_admin_headers()
    org_payload = {
        "name": "TEST MULTI BRANCH HEALTHCARE HQ",
        "display_name": "Multi Branch Healthcare HQ",
        "category": "HOSPITAL",
        "sub_category": "MULTISPECIALTY",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "address": "1 HQ Tower, Anna Salai",
        "pincode": "600002",
        "website_url": "https://multibranchhealth.com",
        "branches": [
            {
                "branch_name": "Puducherry Branch",
                "country": "India",
                "state": "Puducherry UT",
                "district": "Puducherry",
                "city": "Puducherry",
                "address": "45 Beach Promenade",
                "pincode": "605001",
                "phone_numbers": ["0413-1112233"]
            },
            {
                "branch_name": "Karaikal Branch",
                "country": "India",
                "state": "Puducherry UT",
                "district": "Karaikal",
                "city": "Karaikal",
                "address": "88 Port Road",
                "pincode": "609602",
                "phone_numbers": ["04368-444555"]
            }
        ]
    }

    res_create = client.post("/api/admin/organizations", json=org_payload, headers=headers)
    assert res_create.status_code in (200, 201)
    org_id = res_create.json()["id"]

    try:
        # 1. Search hospital in Puducherry
        res_pud = client.get("/api/search/fast?category=hospital&location=Puducherry&limit=20")
        assert res_pud.status_code == 200
        pud_results = [r for r in res_pud.json()["results"] if r.get("organization_id") == org_id or r.get("id") == org_id]
        assert len(pud_results) == 1, "Only Puducherry branch should qualify for Puducherry search"
        pud_match = pud_results[0]
        assert pud_match["branch_name"] == "Puducherry Branch"
        assert pud_match["district"] == "Puducherry"
        assert pud_match["branch_id"] is not None

        # 2. Search hospital in Karaikal
        res_kar = client.get("/api/search/fast?category=hospital&location=Karaikal&limit=20")
        assert res_kar.status_code == 200
        kar_results = [r for r in res_kar.json()["results"] if r.get("organization_id") == org_id or r.get("id") == org_id]
        assert len(kar_results) == 1, "Only Karaikal branch should qualify for Karaikal search"
        kar_match = kar_results[0]
        assert kar_match["branch_name"] == "Karaikal Branch"
        assert kar_match["district"] == "Karaikal"
        assert kar_match["branch_id"] is not None

        # 3. Search hospital in Erode
        res_erode = client.get("/api/search/fast?category=hospital&location=Erode&limit=20")
        assert res_erode.status_code == 200
        erode_results = [r for r in res_erode.json()["results"] if r.get("organization_id") == org_id or r.get("id") == org_id]
        assert len(erode_results) == 0, "Neither branch nor HQ should qualify for Erode search"

    finally:
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)


def test_admin_org_crud_full_lifecycle():
    """
    Test 4: Full Admin Organization CRUD API operations.
    Create -> Read -> Update -> Delete.
    """
    headers = get_admin_headers()
    # Create
    payload = {
        "name": "TEST CRUD SCHOOL",
        "category": "SCHOOL",
        "sub_category": "MATRICULATION",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "address": "50 Avinashi Road",
        "pincode": "641004"
    }
    res_post = client.post("/api/admin/organizations", json=payload, headers=headers)
    assert res_post.status_code in (200, 201)
    org_id = res_post.json()["id"]

    # Read Single
    res_get = client.get(f"/api/admin/organizations/{org_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "TEST CRUD SCHOOL"

    # Update
    update_payload = {
        "name": "TEST CRUD SCHOOL UPDATED",
        "display_name": "Updated CRUD School",
        "sub_category": "CBSE",
        "phone_numbers": [{"raw_value": "0422-5554433", "type": "MAIN"}]
    }
    res_put = client.put(f"/api/admin/organizations/{org_id}", json=update_payload, headers=headers)
    assert res_put.status_code == 200
    assert res_put.json()["name"] == "TEST CRUD SCHOOL UPDATED"
    assert res_put.json()["display_name"] == "Updated CRUD School"
    assert res_put.json()["sub_category"] == "CBSE"

    # Read List
    res_list = client.get("/api/admin/organizations?search=TEST+CRUD", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["total_records"] >= 1

    # Delete
    res_del = client.delete(f"/api/admin/organizations/{org_id}", headers=headers)
    assert res_del.status_code == 200

    # Verify Deletion
    res_get_deleted = client.get(f"/api/admin/organizations/{org_id}", headers=headers)
    assert res_get_deleted.status_code == 404


