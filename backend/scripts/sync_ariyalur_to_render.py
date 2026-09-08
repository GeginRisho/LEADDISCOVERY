import os
import sys
import time
import httpx
from typing import Dict, Any, List

# Add backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.models import Organization

RENDER_API_BASE = "https://leaddiscovery.onrender.com"

def sync_ariyalur():
    print("=========================================================================")
    print("       SYNCING ARIYALUR 122 VERIFIED ORGANIZATIONS TO RENDER DB         ")
    print("=========================================================================")

    # 1. Fetch 122 local Ariyalur organizations
    local_db = SessionLocal()
    try:
        local_orgs: List[Organization] = local_db.query(Organization).filter(
            Organization.district == "Ariyalur",
            Organization.is_quarantined.isnot(True)
        ).all()
        print(f"Local Ariyalur Verified Orgs Count: {len(local_orgs)}")
        
        org_payloads = []
        for org in local_orgs:
            payload = {
                "name": org.name,
                "display_name": org.display_name,
                "category": org.category,
                "sub_category": org.sub_category,
                "description": org.description,
                "district": org.district,
                "state": org.state,
                "city": org.city or "Ariyalur",
                "address": org.address,
                "country": org.country or "India",
                "pincode": org.pincode,
                "official_website_url": org.official_website_url,
                "google_maps_url": org.google_maps_url,
                "phone_numbers": [{"raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type} for p in org.phone_numbers],
                "emails": [{"email": e.email, "type": e.type} for e in org.email_addresses],
                "confidence": "HIGH"
            }
            org_payloads.append(payload)
    finally:
        local_db.close()

    if len(org_payloads) != 122:
        print(f"ERROR: Expected 122 local Ariyalur orgs, found {len(org_payloads)}. Aborting sync.")
        return

    # 2. Login to Render
    print("\nLogging into Render production backend...")
    client = httpx.Client(base_url=RENDER_API_BASE, timeout=60.0)
    login_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if login_res.status_code != 200:
        print(f"ERROR: Failed to login to Render: {login_res.status_code} - {login_res.text}")
        return

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Authenticated successfully as Admin on Render.")

    # 3. Inspect existing Ariyalur organizations on Render
    list_res = client.get("/api/admin/organizations?district=Ariyalur&limit=200", headers=headers)
    existing_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    print(f"\nFound {len(existing_items)} existing Ariyalur organizations on Render.")

    # Delete existing junk items (search snippets, california colleges, etc.)
    valid_local_names = {p["name"].strip().lower() for p in org_payloads}
    for item in existing_items:
        item_id = item["id"]
        item_name = item.get("name", "").strip()
        if item_name.lower() not in valid_local_names:
            print(f"Deleting invalid/junk record from Render: [ID {item_id}] {item_name}")
            del_res = client.delete(f"/api/admin/organizations/{item_id}", headers=headers)
            if del_res.status_code not in (200, 204, 404):
                print(f"  Warning: failed to delete {item_id}: {del_res.status_code}")

    # Re-fetch after cleanup
    list_res = client.get("/api/admin/organizations?district=Ariyalur&limit=200", headers=headers)
    current_render_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    current_render_names = {item.get("name", "").strip().lower(): item["id"] for item in current_render_items}

    # 4. Insert missing valid Ariyalur organizations
    print(f"\nInserting verified Ariyalur organizations into Render...")
    inserted_count = 0
    skipped_count = 0

    for payload in org_payloads:
        p_name = payload["name"].strip()
        if p_name.lower() in current_render_names:
            skipped_count += 1
            continue

        res = client.post("/api/admin/organizations", json=payload, headers=headers)
        if res.status_code in (200, 201):
            inserted_count += 1
            if inserted_count % 10 == 0 or inserted_count == len(org_payloads):
                print(f"  Inserted {inserted_count} organizations...")
        else:
            print(f"  Failed to insert '{p_name}': {res.status_code} - {res.text}")

    print(f"\nSync Complete! Inserted: {inserted_count}, Skipped (Already Present): {skipped_count}")

    # 5. Verify Regional Matrix counts directly from Render
    print("\nVerifying Regional Matrix on Render...")
    matrix_res = client.get("/api/organizations/districts")
    if matrix_res.status_code == 200:
        matrix = matrix_res.json()
        ariyalur_row = next((r for r in matrix if r.get("district_name") == "Ariyalur"), None)
        if ariyalur_row:
            print("\n-------------------------------------------------------------")
            print("  RENDER REGIONAL MATRIX ROW FOR ARIYALUR:")
            print(f"  Colleges:     {ariyalur_row.get('colleges_count')}")
            print(f"  Schools:      {ariyalur_row.get('schools_count')}")
            print(f"  Hotels:       {ariyalur_row.get('hotels_count')}")
            print(f"  Hospitals:    {ariyalur_row.get('hospitals_count')}")
            print(f"  Companies:    {ariyalur_row.get('companies_count')}")
            print(f"  IT Companies: {ariyalur_row.get('it_companies_count')}")
            print(f"  TOTAL:        {ariyalur_row.get('total_organizations')}")
            print("-------------------------------------------------------------\n")
        else:
            print("ERROR: Ariyalur not found in Render district matrix.")
    else:
        print(f"ERROR: Failed to fetch matrix: {matrix_res.status_code}")

if __name__ == "__main__":
    sync_ariyalur()
