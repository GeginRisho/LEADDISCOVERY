import os
import sys
import asyncio
import httpx
from typing import Dict, Any, List

# Add backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.models import Organization

RENDER_API_BASE = "https://leaddiscovery.onrender.com"

DISTRICT_TARGETS = {
    "Coimbatore": 181,
    "Cuddalore": 124,
    "Dharmapuri": 116,
}

async def sync_district_async(district_name: str, expected_count: int, client: httpx.AsyncClient, headers: Dict[str, str]):
    print(f"\n=========================================================================")
    print(f"       FAST ASYNC SYNCING {district_name.upper()} ({expected_count} VERIFIED ORGS)   ")
    print(f"=========================================================================")

    # 1. Fetch local organizations
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

    if len(org_payloads) != expected_count:
        print(f"ERROR: Expected {expected_count} local {district_name} orgs, found {len(org_payloads)}. Aborting.")
        return False

    # 2. Inspect existing organizations on Render
    list_res = await client.get(f"/api/admin/organizations?district={district_name}&limit=350", headers=headers)
    existing_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    print(f"Found {len(existing_items)} existing {district_name} organizations on Render.")

    valid_local_names = {p["name"].strip().lower() for p in org_payloads}
    for item in existing_items:
        item_id = item["id"]
        item_name = item.get("name", "").strip()
        if item_name.lower() not in valid_local_names:
            print(f"  Deleting invalid/unverified record from Render: [ID {item_id}] {item_name}")
            await client.delete(f"/api/admin/organizations/{item_id}", headers=headers)

    # Re-fetch after cleanup
    list_res = await client.get(f"/api/admin/organizations?district={district_name}&limit=350", headers=headers)
    current_render_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    current_render_names = {item.get("name", "").strip().lower(): item["id"] for item in current_render_items}

    # 3. Filter payloads that need insertion
    to_insert = [p for p in org_payloads if p["name"].strip().lower() not in current_render_names]
    print(f"Need to insert {len(to_insert)} organizations for {district_name} (already present: {len(current_render_names)})")

    sem = asyncio.Semaphore(10)
    inserted_counter = 0

    async def insert_single(payload: dict):
        nonlocal inserted_counter
        async with sem:
            p_name = payload["name"].strip()
            try:
                res = await client.post("/api/admin/organizations", json=payload, headers=headers, timeout=30.0)
                if res.status_code in (200, 201):
                    inserted_counter += 1
                    if inserted_counter % 20 == 0 or inserted_counter == len(to_insert):
                        print(f"  [{district_name}] Inserted {inserted_counter}/{len(to_insert)}...")
                else:
                    print(f"  [{district_name}] Failed to insert '{p_name}': {res.status_code} - {res.text[:100]}")
            except Exception as e:
                print(f"  [{district_name}] Exception inserting '{p_name}': {e}")

    await asyncio.gather(*(insert_single(p) for p in to_insert))
    print(f"Sync Complete for {district_name}! Total present: {len(current_render_names) + inserted_counter}")
    return True

async def main_async():
    print("\nLogging into Render production backend...")
    async with httpx.AsyncClient(base_url=RENDER_API_BASE, timeout=60.0) as client:
        login_res = await client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
        if login_res.status_code != 200:
            print(f"ERROR: Failed to login to Render: {login_res.status_code}")
            return

        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated successfully on Render.")

        # Sync sequentially per district to avoid overwhelming the Render pooler
        for district, count in DISTRICT_TARGETS.items():
            await sync_district_async(district, count, client, headers)

        # Verify Regional Matrix on Render
        print("\nVerifying Regional Matrix on Render...")
        matrix_res = await client.get("/api/organizations/districts")
        if matrix_res.status_code == 200:
            matrix = matrix_res.json()
            print("\n" + "=" * 90)
            print(f"{'REGION':<20} | {'COLLEGES':<9} | {'SCHOOLS':<9} | {'HOTELS':<8} | {'HOSPITALS':<9} | {'COMPANIES':<9} | {'IT':<4} | {'TOTAL'}")
            print("-" * 90)
            for target in ["Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri"]:
                row = next((r for r in matrix if r.get("district_name") == target), None)
                if row:
                    print(f"{target:<20} | {row.get('colleges_count', 0):<9} | {row.get('schools_count', 0):<9} | {row.get('hotels_count', 0):<8} | {row.get('hospitals_count', 0):<9} | {row.get('companies_count', 0):<9} | {row.get('it_companies_count', 0):<4} | {row.get('total_organizations', 0)}")
            print("=" * 90 + "\n")
        else:
            print(f"ERROR: Failed to fetch matrix: {matrix_res.status_code}")

if __name__ == "__main__":
    asyncio.run(main_async())
