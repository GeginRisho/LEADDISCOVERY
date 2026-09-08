import os
import sys
import time
import httpx
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.models import Organization, EmailAddress

RENDER_API_BASE = "https://leaddiscovery.onrender.com"

def main():
    print("=========================================================================")
    print("          SYNCING VERIFIED EMAILS TO RENDER NEON POSTGRESQL              ")
    print("=========================================================================")

    # 1. Fetch local organizations that have emails
    local_db = SessionLocal()
    try:
        orgs_with_emails = local_db.query(Organization).join(EmailAddress).distinct().all()
        print(f"Found {len(orgs_with_emails)} organizations with verified emails in local master database.")

        sync_payloads = []
        total_email_records = 0
        for org in orgs_with_emails:
            emails = [{"email": e.email.strip(), "extraction_method": e.extraction_method or "OFFICIAL_REGISTRY"} for e in org.email_addresses if e.email]
            if emails:
                sync_payloads.append({
                    "name": org.name.strip(),
                    "district": (org.district or "").strip(),
                    "emails": emails
                })
                total_email_records += len(emails)

        print(f"Prepared {total_email_records} email entries across {len(sync_payloads)} organizations.")
    finally:
        local_db.close()

    # 2. Authenticate on Render
    client = httpx.Client(base_url=RENDER_API_BASE, timeout=60.0)
    print("Logging into Render production backend...")
    login_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    if login_res.status_code != 200:
        print(f"ERROR: Failed to login to Render: {login_res.status_code} - {login_res.text}")
        return

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Successfully authenticated as Admin on Render.")

    # 3. Post batches to /api/admin/organizations/bulk-sync-emails
    batch_size = 50
    total_synced = 0
    for i in range(0, len(sync_payloads), batch_size):
        batch = sync_payloads[i:i + batch_size]
        res = client.post("/api/admin/organizations/bulk-sync-emails", json={"items": batch}, headers=headers)
        if res.status_code == 200:
            data = res.json()
            total_synced += data.get("synced_organizations", 0)
            print(f"Batch {i // batch_size + 1}/{(len(sync_payloads) + batch_size - 1) // batch_size}: {data.get('message')} | Total emails in DB: {data.get('total_emails_now')}")
        else:
            print(f"Batch {i // batch_size + 1} failed: {res.status_code} - {res.text[:200]}")
        time.sleep(0.3)

    # 4. Check final statistics on Render
    stats_res = client.get("/api/organizations/stats", headers=headers)
    if stats_res.status_code == 200:
        print("\nUpdated Production Statistics on Render:")
        print(stats_res.json())
    else:
        print(f"Failed to fetch updated stats: {stats_res.status_code}")

if __name__ == "__main__":
    main()
