"""
Population script for the final 9 regions:
1. Tirupathur
2. Tiruppur
3. Tiruvallur
4. Tiruvannamalai
5. Tiruvarur
6. Vellore
7. Viluppuram
8. Virudhunagar
9. Puducherry UT
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
from scripts.data.tirupathur_data import TIRUPATHUR_DATA
from scripts.data.tiruppur_data import TIRUPPUR_DATA
from scripts.data.tiruvallur_data import TIRUVALLUR_DATA
from scripts.data.tiruvannamalai_data import TIRUVANNAMALAI_DATA
from scripts.data.tiruvarur_data import TIRUVARUR_DATA
from scripts.data.vellore_data import VELLORE_DATA
from scripts.data.viluppuram_data import VILUPPURAM_DATA
from scripts.data.virudhunagar_data import VIRUDHUNAGAR_DATA
from scripts.data.puducherry_data import PUDUCHERRY_DATA

REGION_DATASETS = [
    ("Tirupathur", TIRUPATHUR_DATA, "Tamil Nadu"),
    ("Tiruppur", TIRUPPUR_DATA, "Tamil Nadu"),
    ("Tiruvallur", TIRUVALLUR_DATA, "Tamil Nadu"),
    ("Tiruvannamalai", TIRUVANNAMALAI_DATA, "Tamil Nadu"),
    ("Tiruvarur", TIRUVARUR_DATA, "Tamil Nadu"),
    ("Vellore", VELLORE_DATA, "Tamil Nadu"),
    ("Viluppuram", VILUPPURAM_DATA, "Tamil Nadu"),
    ("Virudhunagar", VIRUDHUNAGAR_DATA, "Tamil Nadu"),
    ("Puducherry", PUDUCHERRY_DATA, "Puducherry UT"),
]

def clean_puducherry_junk(db):
    junk_ids = [1599, 1600, 1601, 1602, 1811, 2056, 5483]
    junk_orgs = db.query(Organization).filter(Organization.id.in_(junk_ids)).all()
    for o in junk_orgs:
        o.is_quarantined = True
    db.commit()
    print(f"Quarantined {len(junk_orgs)} junk non-organization records in Puducherry.")

def populate_region(region_name: str, org_list: List[Dict[str, Any]], state_name: str, db):
    print(f"\nProcessing {region_name} ({len(org_list)} target records)...")
    
    existing_orgs = db.query(Organization).filter(Organization.district == region_name).all()
    existing_by_name = {o.name.strip().lower(): o for o in existing_orgs}
    
    inserted = 0
    updated = 0
    
    for item in org_list:
        clean_name = item["name"].strip()
        name_key = clean_name.lower()
        web_url = item.get("official_website_url") or item.get("website_url")
        phone_num = item.get("phone")
        email_addr = item.get("email")
        
        existing = existing_by_name.get(name_key)
        
        if existing:
            existing.display_name = item.get("display_name", clean_name)
            existing.category = item["category"]
            existing.sub_category = item.get("sub_category", existing.sub_category)
            existing.description = item.get("description", existing.description)
            existing.district = region_name
            existing.state = item.get("state", state_name)
            existing.country = "India"
            existing.city = item.get("city", existing.city or region_name)
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
                district=region_name,
                state=item.get("state", state_name),
                country="India",
                city=item.get("city", region_name),
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
                verified_at=datetime.datetime.utcnow(),
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
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
                
        if phone_num:
            phone = db.query(PhoneNumber).filter(PhoneNumber.organization_id == org_id, PhoneNumber.normalized_value == phone_num).first()
            if not phone:
                phone = PhoneNumber(
                    organization_id=org_id,
                    raw_value=phone_num,
                    normalized_value=phone_num,
                    type="main"
                )
                db.add(phone)
                
        if email_addr:
            email = db.query(EmailAddress).filter(EmailAddress.organization_id == org_id, EmailAddress.email == email_addr).first()
            if not email:
                email = EmailAddress(
                    organization_id=org_id,
                    email=email_addr,
                    extraction_method="OFFICIAL_REGISTRY"
                )
                db.add(email)
                
    db.commit()
    print(f"[{region_name}] Done! Inserted: {inserted}, Updated/Enriched: {updated}")

def main():
    db = SessionLocal()
    try:
        clean_puducherry_junk(db)
        for r_name, r_data, state_name in REGION_DATASETS:
            populate_region(r_name, r_data, state_name, db)
        print("\nAll 9 final regions populated successfully in local PostgreSQL.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
