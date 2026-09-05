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
    print("Starting Master Database Audit & Data Cleanup...")

    purged_web_count = 0
    purged_org_count = 0

    # 1. Audit Websites table
    all_websites = db.query(Website).all()
    for web in all_websites:
        domain = (web.domain or "").lower().strip()
        url_domain = extract_domain(web.url or "")
        
        if is_directory_domain(domain) or is_directory_domain(url_domain) or "wikivoyage" in domain or "wikivoyage" in url_domain:
            print(f"[PURGE WEBSITE] Org ID {web.organization_id} website domain '{domain}' / url '{web.url}' is blacklisted portal.")
            web.url = ""
            web.status = "NO_OFFICIAL_WEBSITE"
            web.reason = "Blacklisted portal domain removed"
            purged_web_count += 1

    # 2. Audit Organizations table
    all_orgs = db.query(Organization).all()
    for org in all_orgs:
        is_real, id_reason, meta = verify_organization_identity(
            name=org.name,
            url=org.official_website_url or org.discovery_source_url or ""
        )
        
        if not is_real or any(bad in org.name.lower() for bad in ["wikivoyage", "wikipedia", "travel guide", "dictionary", "results 20"]):
            safe_name = org.name.encode("ascii", "ignore").decode("ascii")
            print(f"[PURGE ORGANISATION] Deleting invalid record ID {org.id}: '{safe_name}' (Reason: {id_reason})")
            db.delete(org)
            purged_org_count += 1
        else:
            # Backfill normalized category and sub_category
            from app.services.scraper.identification import normalize_category_and_subcategory
            cat_str = org.category or (org.task.keyword if org.task else "SCHOOL")
            norm_cat, norm_subcat = normalize_category_and_subcategory(cat_str)
            org.category = norm_cat
            org.sub_category = norm_subcat
            
            # Ensure verification flags & high confidence on clean orgs with official website
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
    
    # Recalculate counters for all existing tasks
    from app.services.scraper.worker import sync_task_counters
    all_tasks = db.query(ScrapingTask).all()
    for t in all_tasks:
        sync_task_counters(db, t.id)

    db.close()
    print(f"Cleanup complete! Purged {purged_org_count} non-organizations and cleaned {purged_web_count} bad website domains.")

if __name__ == "__main__":
    audit_and_cleanup_database()
