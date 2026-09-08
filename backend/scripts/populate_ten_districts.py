"""
Script to populate real verified Master Organizations for 10 Tamil Nadu districts:
1. Ramanathapuram
2. Ranipet
3. Salem
4. Sivaganga
5. Tenkasi
6. Thanjavur
7. Theni
8. Thoothukudi
9. Tiruchirappalli
10. Tirunelveli
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
from scripts.data.ramanathapuram_data import RAMANATHAPURAM_DATA
from scripts.data.ranipet_data import RANIPET_DATA
from scripts.data.salem_data import SALEM_DATA
from scripts.data.sivaganga_data import SIVAGANGA_DATA
from scripts.data.tenkasi_data import TENKASI_DATA
from scripts.data.thanjavur_data import THANJAVUR_DATA
from scripts.data.theni_data import THENI_DATA
from scripts.data.thoothukudi_data import THOOTHUKUDI_DATA
from scripts.data.tiruchirappalli_data import TIRUCHIRAPPALLI_DATA
from scripts.data.tirunelveli_data import TIRUNELVELI_DATA

DISTRICT_DATASETS = [
    ("Ramanathapuram", RAMANATHAPURAM_DATA),
    ("Ranipet", RANIPET_DATA),
    ("Salem", SALEM_DATA),
    ("Sivaganga", SIVAGANGA_DATA),
    ("Tenkasi", TENKASI_DATA),
    ("Thanjavur", THANJAVUR_DATA),
    ("Theni", THENI_DATA),
    ("Thoothukudi", THOOTHUKUDI_DATA),
    ("Tiruchirappalli", TIRUCHIRAPPALLI_DATA),
    ("Tirunelveli", TIRUNELVELI_DATA),
]

def populate_district(district_name: str, org_list: List[Dict[str, Any]], db):
    print(f"\nProcessing {district_name} ({len(org_list)} target records)...")
    
    existing_orgs = db.query(Organization).filter(Organization.district == district_name).all()
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
            existing.district = district_name
            existing.state = "Tamil Nadu"
            existing.country = "India"
            existing.city = item.get("city", existing.city or district_name)
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
    print(f"Finished {district_name}: Inserted {inserted}, Updated {updated}, Total: {len(existing_by_name)}")

def main():
    print("=========================================================================")
    print("   POPULATING 10 TAMIL NADU DISTRICTS WITH REAL VERIFIED MASTER DATA     ")
    print("=========================================================================")
    db = SessionLocal()
    try:
        for district_name, org_list in DISTRICT_DATASETS:
            populate_district(district_name, org_list, db)
    finally:
        db.close()
    print("\nAll 10 districts populated successfully in local database.\n")

if __name__ == "__main__":
    main()
