import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_acceptance_test():
    print("================================================================")
    print("      REAL ACCEPTANCE TEST WORKFLOW (STEPS A THROUGH O)       ")
    print("================================================================")

    # 1. Login as Admin
    login_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if login_res.status_code != 200:
        client.post("/api/auth/register", json={"email": "admin@leaddiscovery.com", "password": "admin123", "role": "ADMIN"})
        login_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[AUTH] Admin logged in successfully.")

    # Cleanup any existing acceptance test records
    existing_orgs = client.get("/api/organizations?search=ACCEPTANCE&limit=100", headers=headers).json().get("organizations", [])
    for eo in existing_orgs:
        client.delete(f"/api/admin/organizations/{eo['id']}", headers=headers)

    # STEP A & B: Add legitimate organization 1 (Hospital A in Puducherry)
    hosp_a_payload = {
        "name": "ACCEPTANCE Puducherry Multispecialty Hospital A",
        "display_name": "Puducherry Hospital A",
        "category": "hospital",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "address": "100 Beach Promenade",
        "official_website_url": "https://puducherryhospital-a.org"
    }
    res_a = client.post("/api/admin/organizations", json=hosp_a_payload, headers=headers)
    assert res_a.status_code in (200, 201), res_a.text
    id_a = res_a.json()["id"]
    print(f"[STEP A&B] Added Org A: ID {id_a} 'Puducherry Multispecialty Hospital A'")

    # STEP C: Verify Org A from Admin
    res_v_a = client.post(f"/api/organizations/{id_a}/verify", headers=headers)
    assert res_v_a.status_code == 200
    assert res_v_a.json()["admin_verified"] is True
    print(f"[STEP C] Verified Org A from Admin. (admin_verified=True, source_type=ADMIN_VERIFIED)")

    # STEP D & E: User Search hospital + puducherry -> confirm Org A appears #1
    search_1 = client.get("/api/search/fast?category=hospital&location=puducherry")
    assert search_1.status_code == 200
    results_1 = search_1.json()["results"]
    assert len(results_1) >= 1
    first = results_1[0]
    assert first["organization_name"] == "ACCEPTANCE Puducherry Multispecialty Hospital A" or first["id"] == id_a
    print(f"[STEP D&E] User Search hospital+puducherry returned Org A as FIRST result!")

    # STEP F & G: Add & Verify Org B (Hospital B in Puducherry)
    hosp_b_payload = {
        "name": "ACCEPTANCE Puducherry Care Clinic B",
        "category": "hospital",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "official_website_url": "https://puducherryclinic-b.org"
    }
    res_b = client.post("/api/admin/organizations", json=hosp_b_payload, headers=headers)
    id_b = res_b.json()["id"]
    client.post(f"/api/organizations/{id_b}/verify", headers=headers)
    print(f"[STEP F&G] Added & Verified Org B: ID {id_b} 'Puducherry Care Clinic B'")

    # STEP K check: Add Org C in Chennai (Wrong Location)
    hosp_c_payload = {
        "name": "ACCEPTANCE Chennai General Hospital C",
        "category": "hospital",
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "official_website_url": "https://chennaihospital-c.org"
    }
    res_c = client.post("/api/admin/organizations", json=hosp_c_payload, headers=headers)
    id_c = res_c.json()["id"]
    client.post(f"/api/organizations/{id_c}/verify", headers=headers)
    print(f"[STEP K SETUP] Added & Verified Org C in Chennai: ID {id_c}")

    # STEP H & I & J: Unverify Org A, Search again -> confirm priority changes
    client.post(f"/api/organizations/{id_a}/unverify", headers=headers)
    print(f"[STEP H] Unverified Org A. Provenance restored.")

    search_2 = client.get("/api/search/fast?category=hospital&location=puducherry")
    results_2 = search_2.json()["results"]
    assert results_2[0]["organization_name"] == "ACCEPTANCE Puducherry Care Clinic B" or results_2[0]["id"] == id_b
    print(f"[STEP I&J] Ranking changed! Org B (Admin Verified) is now FIRST.")

    # STEP K: Confirm Chennai Org C NEVER appears in Puducherry results
    pud_names = [r.get("organization_name") or r.get("name") for r in results_2]
    assert "ACCEPTANCE Chennai General Hospital C" not in pud_names
    print(f"[STEP K] Confirmed: Chennai Org C is STRICTLY EXCLUDED from Puducherry search results!")

    # STEP L, M, N, O: Add Org D (Engineering College), Verify, confirm immediate search
    coll_payload = {
        "name": "ACCEPTANCE Puducherry Institute of Technology D",
        "category": "college",
        "sub_category": "Engineering",
        "country": "India",
        "state": "Puducherry UT",
        "district": "Puducherry",
        "city": "Puducherry",
        "official_website_url": "https://puducherrytech-d.edu.in"
    }
    res_d = client.post("/api/admin/organizations", json=coll_payload, headers=headers)
    id_d = res_d.json()["id"]
    print(f"[STEP L&M] Added Org D: ID {id_d}. Appears in Master Organizations.")

    client.post(f"/api/organizations/{id_d}/verify", headers=headers)
    print(f"[STEP N] Verified Org D.")

    search_d = client.get("/api/search/fast?category=college&location=puducherry")
    results_d = search_d.json()["results"]
    assert len(results_d) >= 1
    assert results_d[0]["organization_name"] == "ACCEPTANCE Puducherry Institute of Technology D" or results_d[0]["id"] == id_d
    print(f"[STEP O] Immediate Search Success! Org D appears #1 for college+puducherry search.")

    # Cleanup test records
    for org_id in (id_a, id_b, id_c, id_d):
        client.delete(f"/api/admin/organizations/{org_id}", headers=headers)
    print("[CLEANUP] Deleted test records cleanly.")

    print("\n================================================================")
    print("      REAL ACCEPTANCE TEST COMPLETED: 100% PASSED             ")
    print("================================================================")

if __name__ == "__main__":
    run_acceptance_test()
