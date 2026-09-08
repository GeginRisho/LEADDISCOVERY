"""
Sync the final 9 regions:
1. Tirupathur
2. Tiruppur
3. Tiruvallur
4. Tiruvannamalai
5. Tiruvarur
6. Vellore
7. Viluppuram
8. Virudhunagar
9. Puducherry UT
to Render production PostgreSQL database.
"""

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

REGIONS_TO_SYNC = [
    "Tirupathur",
    "Tiruppur",
    "Tiruvallur",
    "Tiruvannamalai",
    "Tiruvarur",
    "Vellore",
    "Viluppuram",
    "Virudhunagar",
    "Puducherry"
]

async def sync_region_async(region_name: str, client: httpx.AsyncClient, headers: Dict[str, str]):
    print(f"\n=========================================================================")
    print(f"       ASYNC SYNCING {region_name.upper()} TO RENDER PRODUCTION DB       ")
    print(f"=========================================================================")

    # 1. Fetch local verified organizations
    local_db = SessionLocal()
    try:
        local_orgs: List[Organization] = local_db.query(Organization).filter(
            Organization.district == region_name,
            Organization.is_quarantined.isnot(True)
        ).all()
        print(f"Local {region_name} Verified Orgs Count: {len(local_orgs)}")

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
                "city": org.city or region_name,
                "address": org.address,
                "country": org.country or "India",
                "pincode": org.pincode,
                "official_website_url": org.official_website_url,
                "google_maps_url": org.google_maps_url,
                "phone_numbers": [{"raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type} for p in org.phone_numbers],
                "emails": [{"email": e.email, "type": getattr(e, 'type', 'main')} for e in org.email_addresses],
                "confidence": "HIGH"
            }
            org_payloads.append(payload)
    finally:
        local_db.close()

    # 2. Inspect existing organizations on Render
    list_res = await client.get(f"/api/admin/organizations?district={region_name}&limit=400", headers=headers)
    existing_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    print(f"Found {len(existing_items)} existing {region_name} organizations on Render.")

    valid_local_names = {p["name"].strip().lower() for p in org_payloads}
    for item in existing_items:
        item_id = item["id"]
        item_name = item.get("name", "").strip()
        if item_name.lower() not in valid_local_names:
            print(f"  Deleting unverified/mismatched record from Render: [ID {item_id}] {item_name}")
            await client.delete(f"/api/admin/organizations/{item_id}", headers=headers)

    # Re-fetch after cleanup
    list_res = await client.get(f"/api/admin/organizations?district={region_name}&limit=400", headers=headers)
    current_render_items = list_res.json().get("items", []) if list_res.status_code == 200 else []
    current_render_names = {item.get("name", "").strip().lower(): item["id"] for item in current_render_items}

    # 3. Filter payloads that need insertion
    to_insert = [p for p in org_payloads if p["name"].strip().lower() not in current_render_names]
    print(f"Organizations to insert into Render: {len(to_insert)}")

    sem = asyncio.Semaphore(5)

    async def insert_one(p):
        async with sem:
            try:
                res = await client.post("/api/admin/organizations", json=p, headers=headers)
                if res.status_code in (200, 201):
                    return True
                elif res.status_code == 400 and "already exists" in res.text:
                    return True
                else:
                    print(f"Failed to insert {p['name']}: {res.status_code} - {res.text[:100]}", flush=True)
                    return False
            except Exception as e:
                print(f"Exception inserting {p['name']}: {e}", flush=True)
                return False

    if to_insert:
        # Process in batches of 20 with small delay
        success_count = 0
        batch_size = 20
        for i in range(0, len(to_insert), batch_size):
            chunk = to_insert[i:i + batch_size]
            results = await asyncio.gather(*[insert_one(p) for p in chunk])
            success_count += sum(1 for r in results if r)
            print(f"  [{region_name}] Progress: {success_count}/{len(to_insert)} records synced...", flush=True)
            await asyncio.sleep(0.2)
        print(f"Successfully inserted {success_count}/{len(to_insert)} records into Render for {region_name}.", flush=True)
    else:
        print(f"All {region_name} records already present on Render.", flush=True)

async def main():
    print("=========================================================================")
    print("  CONNECTING TO RENDER CLOUD PLATFORM (https://leaddiscovery.onrender.com)  ")
    print("=========================================================================")

    async with httpx.AsyncClient(base_url=RENDER_API_BASE, timeout=60.0) as client:
        # Authenticate on Render
        login_res = await client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
        if login_res.status_code != 200:
            print(f"Authentication failed: {login_res.status_code} - {login_res.text}")
            return

        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated successfully as admin@leaddiscovery.com on Render.")

        # Sync each region
        for r_name in REGIONS_TO_SYNC:
            await sync_region_async(r_name, client, headers)

        # Audit Render Regional Matrix
        print("\n=========================================================================")
        print("       FETCHING UPDATED REGIONAL MATRIX DIRECTLY FROM RENDER CLOUD       ")
        print("=========================================================================")
        matrix_res = await client.get("/api/organizations/districts")
        if matrix_res.status_code == 200:
            matrix_data = matrix_res.json()
            items = matrix_data.get("items", [])
            print(f"Total Regions in Matrix: {len(items)}")
            header = f"{'Region':<18} | {'Colleges':<8} | {'Schools':<8} | {'Hotels':<8} | {'Hospitals':<8} | {'Companies':<9} | {'IT Companies':<12} | {'Total'}"
            print(header)
            print("-" * len(header))
            for row in items:
                r_name = row.get("district", row.get("name"))
                if r_name in REGIONS_TO_SYNC or r_name == "Puducherry UT":
                    print(f"{r_name:<18} | {row['colleges']:<8} | {row['schools']:<8} | {row['hotels']:<8} | {row['hospitals']:<8} | {row['companies']:<9} | {row['it_companies']:<12} | {row['total']}")
        else:
            print(f"Failed to fetch matrix: {matrix_res.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
