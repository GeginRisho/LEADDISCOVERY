import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient

# Ensure root import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.models.models import Organization
from app.core.database import SessionLocal

client = TestClient(app)

def run_acceptance_tests():
    print("================================================================")
    print("LEADDISCOVERY — REAL-WORLD ACCESS CONTROL ACCEPTANCE VERIFICATION")
    print("================================================================")

    # Clean up existing test organizations from previous runs
    db_cleanup = SessionLocal()
    try:
        db_cleanup.query(Organization).filter(
            Organization.name.in_([
                "Grand Heritage Resort Puducherry",
                "Grand Heritage Resort Chennai",
                "Ocean Breeze Resort Puducherry"
            ])
        ).delete(synchronize_session=False)
        db_cleanup.commit()
    finally:
        db_cleanup.close()

    # 1. Login as Normal User
    print("\n[Step A] Logging in as Normal USER (testuser@leaddiscovery.com)...")
    login_user_res = client.post("/api/auth/login", json={"email": "testuser@leaddiscovery.com", "password": "User@12345"})
    assert login_user_res.status_code == 200, f"User login failed: {login_user_res.text}"
    user_token = login_user_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    me_user = client.get("/api/auth/me", headers=user_headers).json()
    print(f"-> Authenticated User Role: {me_user.get('role')}")
    assert me_user.get("role") == "USER"

    print("-> Attempting to access /api/organizations as Normal USER...")
    orgs_user_res = client.get("/api/organizations", headers=user_headers)
    print(f"-> Status Code: {orgs_user_res.status_code}")
    assert orgs_user_res.status_code == 403, f"Expected 403, got {orgs_user_res.status_code}"
    print("-> PASSED: Normal user is DENIED 403 access to Master Organizations API!")

    # 2. Login as ADMIN
    print("\n[Step B] Logging in as ADMIN (admin@leaddiscovery.com)...")
    login_admin_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    assert login_admin_res.status_code == 200, f"Admin login failed: {login_admin_res.text}"
    admin_token = login_admin_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    me_admin = client.get("/api/auth/me", headers=admin_headers).json()
    print(f"-> Authenticated Admin Role: {me_admin.get('role')}")
    assert me_admin.get("role") == "ADMIN"

    orgs_admin_res = client.get("/api/organizations", headers=admin_headers)
    print(f"-> Status Code: {orgs_admin_res.status_code}")
    assert orgs_admin_res.status_code == 200
    print("-> PASSED: Admin user has 200 OK access to Master Organizations API!")

    # 3. Admin adds legitimate org & verifies it
    print("\n[Step C] Admin adding legitimate organization 'Grand Heritage Resort Puducherry'...")
    add_payload = {
        "name": "Grand Heritage Resort Puducherry",
        "category": "Resort",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "address": "10 Beach Road, Puducherry",
        "official_website": "https://grandheritageresortpuducherry.com",
        "phone": "+91 413 2223344",
        "email": "contact@grandheritageresortpuducherry.com"
    }
    create_res = client.post("/api/organizations/manual", json=add_payload, headers=admin_headers)
    assert create_res.status_code == 201, f"Failed to create org: {create_res.text}"
    org_id = create_res.json()["id"]
    print(f"-> Organization created in PostgreSQL with ID: {org_id}")

    print("-> Admin verifying organization...")
    verify_res = client.post(f"/api/organizations/{org_id}/verify", headers=admin_headers)
    assert verify_res.status_code == 200, f"Failed to verify org: {verify_res.text}"
    print(f"-> PASSED: Admin Verified = {verify_res.json()['admin_verified']}")

    # Create Chennai org to test location exclusion
    chennai_res = client.post("/api/organizations/manual", json={
        "name": "Grand Heritage Resort Chennai",
        "category": "Resort",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "address": "50 ECR, Chennai"
    }, headers=admin_headers)
    chennai_org_id = chennai_res.json()["id"]
    client.post(f"/api/organizations/{chennai_org_id}/verify", headers=admin_headers)

    # Create Scraper Verified org in Puducherry to test ranking order
    db = SessionLocal()
    scraper_org = Organization(
        name="Ocean Breeze Resort Puducherry",
        category="Resort",
        district="Puducherry",
        city="Puducherry",
        state="Puducherry UT",
        country="India",
        admin_verified=False,
        identity_verified=True,
        category_verified=True,
        country_verified=True,
        state_verified=True,
        district_verified=True,
        location_verified=True,
        official_website_verified=True,
        source_type="SCRAPER_VERIFIED",
        confidence="HIGH"
    )
    db.add(scraper_org)
    db.commit()
    db.refresh(scraper_org)
    scraper_org_id = scraper_org.id
    db.close()

    try:
        # 4. Logout / Session Switch
        print("\n[Step D & E] Switched back to Normal USER context...")

        # 5. Normal User Search
        print("\n[Step F] Normal USER performing Fast Search: category='Resort', location='Puducherry'...")
        search_res = client.get("/api/search/fast?category=Resort&location=Puducherry&limit=100", headers=user_headers)
        assert search_res.status_code == 200, f"Fast search failed: {search_res.text}"
        results = search_res.json().get("results", [])
        print(f"-> Returned {len(results)} verified resort(s) in Puducherry.")

        names = [r.get("name") for r in results]
        print(f"-> Search Results Order: {names}")

        # 6. Verification
        print("\n[Step G] Validating Acceptance Rules:")
        assert "Grand Heritage Resort Puducherry" in names, "Admin verified org missing from fast search!"
        assert "Ocean Breeze Resort Puducherry" in names, "Scraper verified org missing from fast search!"
        
        # Rule 1: Admin Verified appears FIRST
        admin_idx = names.index("Grand Heritage Resort Puducherry")
        scraper_idx = names.index("Ocean Breeze Resort Puducherry")
        assert admin_idx < scraper_idx, f"Admin verified org must appear before scraper verified! Admin idx: {admin_idx}, Scraper idx: {scraper_idx}"
        print("-> PASSED RULE 1: Admin-verified org appears BEFORE scraper-verified org!")

        # Rule 2: Wrong location org EXCLUDED
        assert "Grand Heritage Resort Chennai" not in names, "Chennai org must NOT appear when searching Puducherry!"
        print("-> PASSED RULE 2: Wrong location admin-verified org is strictly EXCLUDED!")

    finally:
        # Cleanup
        client.delete(f"/api/organizations/{org_id}", headers=admin_headers)
        client.delete(f"/api/organizations/{chennai_org_id}", headers=admin_headers)
        db_clean = SessionLocal()
        o = db_clean.query(Organization).filter(Organization.id == scraper_org_id).first()
        if o:
            db_clean.delete(o)
            db_clean.commit()
        db_clean.close()

    print("\n================================================================")
    print("ALL REAL-WORLD ACCEPTANCE CRITERIA PASSED SUCCESSFULLY (100%)!")
    print("================================================================")

if __name__ == "__main__":
    run_acceptance_tests()
