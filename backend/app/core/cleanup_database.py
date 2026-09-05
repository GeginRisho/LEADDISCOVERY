import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Organization, Website, TaskLead, ScrapingTask, PhoneNumber, EmailAddress
from app.services.scraper.identity_verification import verify_organization_identity
from app.services.scraper.identification import extract_domain, is_directory_domain

def audit_and_cleanup_database():
    db: Session = SessionLocal()
    print("Starting Master Database Audit & Generic Quarantine Pass...")

    # Execute DDL to ensure new columns exist in PostgreSQL
    from sqlalchemy import text
    try:
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_quarantined BOOLEAN DEFAULT FALSE;"))
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS quarantine_reason TEXT;"))
        db.commit()
    except Exception as DdlErr:
        db.rollback()
        print(f"[DDL NOTICE] Column check: {DdlErr}")

    purged_web_count = 0
    quarantined_org_count = 0

    # 1. Audit Websites table
    all_websites = db.query(Website).all()
    for web in all_websites:
        domain = (web.domain or "").lower().strip()
        url_domain = extract_domain(web.url or "")
        
        if is_directory_domain(domain) or is_directory_domain(url_domain) or "wikivoyage" in domain or "wikivoyage" in url_domain:
            web.url = ""
            web.status = "NO_OFFICIAL_WEBSITE"
            web.reason = "Blacklisted portal domain removed"
            purged_web_count += 1

    # 2. Audit Organizations table (Generic Quarantine Pass)
    from app.services.scraper.identity_verification import classify_candidate_entity, verify_organization_identity
    from app.services.scraper.identification import normalize_category_and_subcategory

    all_orgs = db.query(Organization).all()
    for org in all_orgs:
        entity_type, conf, entity_meta = classify_candidate_entity(
            name=org.name,
            url=org.official_website_url or org.discovery_source_url or ""
        )
        is_real, id_reason, _ = verify_organization_identity(
            name=org.name,
            url=org.official_website_url or org.discovery_source_url or ""
        )
        
        if not is_real or entity_type != "ORGANIZATION":
            org.is_quarantined = True
            org.quarantine_reason = f"GENERIC_QUARANTINE: Entity classified as {entity_type} ({id_reason})"
            quarantined_org_count += 1
        else:
            cat_str = org.category or (org.task.keyword if org.task else "OTHER")
            norm_cat, norm_subcat = normalize_category_and_subcategory(cat_str)
            org.category = norm_cat
            org.sub_category = norm_subcat
            org.is_quarantined = False
            org.quarantine_reason = None
            
            if org.official_website_url and not is_directory_domain(org.official_website_url):
                org.identity_verified = True
                org.category_verified = True
                org.country_verified = True
                org.state_verified = True
                org.district_verified = True
                org.location_verified = True
                org.official_website_verified = True
                org.confidence = "HIGH"

    db.commit()
    
    from app.services.scraper.worker import sync_task_counters
    all_tasks = db.query(ScrapingTask).all()
    for t in all_tasks:
        sync_task_counters(db, t.id)

    db.close()
    print(f"Quarantine pass complete! Quarantined {quarantined_org_count} non-organization records and cleaned {purged_web_count} bad website domain references.")

if __name__ == "__main__":
    audit_and_cleanup_database()
