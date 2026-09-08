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

def sync_district(district_name: str, client: httpx.Client, headers: Dict[str, str]):
    print(f"\n=========================================================================")
    print(f"       SYNCING {district_name.upper()} (122 VERIFIED ORGS) TO RENDER DB  ")
    print(f"=========================================================================")

    # 1. Fetch 122 local organizations
    local_db = SessionLocal()
    try:
        local_orgs: List[Organization] = local_db.query(Organization).filter(
            Organization.district == district_name,
            Organization.is_quarantined.isnot(True)
        ).all()
        print(f"Local {district_name} Verified Orgs Count: {len(local_orgs)}")

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
                "city": org.city or district_name,
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
        print(f"ERROR: Expected 122 local {district_name} orgs, found {len(org_payloads)}. Aborting.")
        return False

    # 2. Inspect existing organizations on Render
    list_res = client.get(f"/api/admin/organizations?district={district_name}&limit=200", headers=headers)
    existing_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    print(f"Found {len(existing_items)} existing {district_name} organizations on Render.")

    valid_local_names = {p["name"].strip().lower() for p in org_payloads}
    for item in existing_items:
        item_id = item["id"]
        item_name = item.get("name", "").strip()
        if item_name.lower() not in valid_local_names:
            print(f"  Deleting invalid/unverified record from Render: [ID {item_id}] {item_name}")
            client.delete(f"/api/admin/organizations/{item_id}", headers=headers)

    # Re-fetch after cleanup
    list_res = client.get(f"/api/admin/organizations?district={district_name}&limit=200", headers=headers)
    current_render_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    current_render_names = {item.get("name", "").strip().lower(): item["id"] for item in current_render_items}

    # 3. Insert missing valid organizations
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
            if inserted_count % 15 == 0 or inserted_count == len(org_payloads):
                print(f"  Inserted {inserted_count} organizations...")
        else:
            print(f"  Failed to insert '{p_name}': {res.status_code} - {res.text}")

    print(f"Sync Complete for {district_name}! Inserted: {inserted_count}, Skipped (Already Present): {skipped_count}")
    return True

def main():
    print("\nLogging into Render production backend...")
    client = httpx.Client(base_url=RENDER_API_BASE, timeout=60.0)
    login_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if login_res.status_code != 200:
        print(f"ERROR: Failed to login to Render: {login_res.status_code}")
        return

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Authenticated successfully on Render.")

    # Sync Chengalpattu & Chennai
    sync_district("Chengalpattu", client, headers)
    sync_district("Chennai", client, headers)

    # Verify Regional Matrix
    print("\nVerifying Regional Matrix on Render...")
    matrix_res = client.get("/api/organizations/districts")
    if matrix_res.status_code == 200:
        matrix = matrix_res.json()
        print("\n" + "=" * 90)
        print(f"{'REGION':<20} | {'COLLEGES':<9} | {'SCHOOLS':<9} | {'HOTELS':<8} | {'HOSPITALS':<9} | {'COMPANIES':<9} | {'IT':<4} | {'TOTAL'}")
        print("-" * 90)
        for target in ["Ariyalur", "Chengalpattu", "Chennai"]:
            row = next((r for r in matrix if r.get("district_name") == target), None)
            if row:
                print(f"{target:<20} | {row.get('colleges_count', 0):<9} | {row.get('schools_count', 0):<9} | {row.get('hotels_count', 0):<8} | {row.get('hospitals_count', 0):<9} | {row.get('companies_count', 0):<9} | {row.get('it_companies_count', 0):<4} | {row.get('total_organizations', 0)}")
        print("=" * 90 + "\n")
    else:
        print(f"ERROR: Failed to fetch matrix: {matrix_res.status_code}")

if __name__ == "__main__":
    main()
