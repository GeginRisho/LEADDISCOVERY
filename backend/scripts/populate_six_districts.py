"""
Script to populate real verified Master Organizations for 6 Tamil Nadu districts:
1. Dindigul (109 orgs)
2. Erode (124 orgs)
3. Kallakurichi (94 orgs)
4. Kancheepuram (123 orgs)
5. Kanniyakumari (117 orgs)
6. Karur (105 orgs)
"""

import os
import sys
import datetime
from typing import List, Dict, Any

# Ensure backend root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.models import Organization, Website, PhoneNumber, EmailAddress

# Import datasets
from scripts.data.dindigul_data import DINDIGUL_ORGS
from scripts.data.erode_data import ERODE_ORGS
from scripts.data.kallakurichi_data import KALLAKURICHI_ORGS
from scripts.data.kancheepuram_data import KANCHEEPURAM_ORGS
from scripts.data.kanniyakumari_data import KANNIYAKUMARI_ORGS
from scripts.data.karur_data import KARUR_ORGS

DISTRICT_DATASETS = [
    ("Dindigul", DINDIGUL_ORGS),
    ("Erode", ERODE_ORGS),
    ("Kallakurichi", KALLAKURICHI_ORGS),
    ("Kancheepuram", KANCHEEPURAM_ORGS),
    ("Kanniyakumari", KANNIYAKUMARI_ORGS),
    ("Karur", KARUR_ORGS)
]

def populate_district(district_name: str, org_list: List[Dict[str, Any]], db):
    print(f"\nProcessing {district_name} ({len(org_list)} targets)...")
    
    existing_orgs = db.query(Organization).filter(Organization.district == district_name).all()
    existing_by_name = {o.name.strip().lower(): o for o in existing_orgs}
    
    inserted = 0
    updated = 0
    
    for item in org_list:
        clean_name = item["name"].strip()
        name_key = clean_name.lower()
        web_url = item.get("official_website_url")
        
        existing = existing_by_name.get(name_key)
        
        if existing:
            existing.display_name = item.get("display_name", clean_name)
            existing.category = item["category"]
            existing.sub_category = item.get("sub_category", existing.sub_category)
            existing.description = item.get("description", existing.description)
            existing.district = district_name
            existing.state = "Tamil Nadu"
            existing.country = "India"
            existing.city = item.get("city", existing.city)
            existing.address = item.get("address", existing.address)
            existing.pincode = item.get("pincode", existing.pincode)
            existing.official_website_url = web_url
            existing.admin_verified = True
            existing.source_type = "SCRAPER_VERIFIED"
            existing.verification_method = "REGULATORY_REGISTRY"
            existing.confidence = "HIGH"
            existing.is_quarantined = False
            existing.identity_verified = True
            existing.category_verified = True
            existing.district_verified = True
            existing.state_verified = True
            existing.country_verified = True
            existing.location_verified = True
            existing.official_website_verified = bool(web_url)
            existing.verified_at = datetime.datetime.utcnow()
            org_id = existing.id
            updated += 1
        else:
            new_org = Organization(
                name=clean_name,
                display_name=item.get("display_name", clean_name),
                category=item["category"],
                sub_category=item.get("sub_category"),
                description=item.get("description"),
                district=district_name,
                state="Tamil Nadu",
                country="India",
                city=item.get("city", district_name),
                address=item.get("address"),
                pincode=item.get("pincode"),
                official_website_url=web_url,
                admin_verified=True,
                source_type="SCRAPER_VERIFIED",
                verification_method="REGULATORY_REGISTRY",
                confidence="HIGH",
                is_quarantined=False,
                identity_verified=True,
                category_verified=True,
                district_verified=True,
                state_verified=True,
                country_verified=True,
                location_verified=True,
                official_website_verified=bool(web_url),
                verified_at=datetime.datetime.utcnow()
            )
            db.add(new_org)
            db.flush()
            org_id = new_org.id
            existing_by_name[name_key] = new_org
            inserted += 1
            
        if web_url:
            domain_part = web_url.replace("https://", "").replace("http://", "").split("/")[0]
            web = db.query(Website).filter(Website.organization_id == org_id).first()
            if not web:
                web = Website(
                    organization_id=org_id,
                    url=web_url,
                    domain=domain_part,
                    status="ACTIVE",
                    confidence="HIGH"
                )
                db.add(web)
                
    db.commit()
    print(f"Finished {district_name}: Inserted {inserted}, Updated {updated}, Total: {len(existing_by_name)}")

def main():
    print("=========================================================================")
    print("   POPULATING 6 TAMIL NADU DISTRICTS WITH REAL VERIFIED MASTER DATA      ")
    print("=========================================================================")
    db = SessionLocal()
    try:
        for district_name, org_list in DISTRICT_DATASETS:
            populate_district(district_name, org_list, db)
    finally:
        db.close()
    print("\nAll 6 districts populated successfully in local database.\n")

if __name__ == "__main__":
    main()
