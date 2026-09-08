import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.models import Organization
from app.api.organizations import classify_org_category
from sqlalchemy import or_, func

def print_table():
    db = SessionLocal()
    try:
        districts = ["Ariyalur", "Chengalpattu", "Chennai"]
        print(f"\n{'REGION':<15}  {'COLLEGES':<8}  {'SCHOOLS':<8}  {'HOTELS':<8}  {'HOSPITALS':<9}  {'COMPANIES':<9}  {'IT':<4}  {'TOTAL'}")
        print("-" * 75)
        for d in districts:
            orgs = db.query(Organization).filter(
                Organization.district == d,
                Organization.is_quarantined.isnot(True),
                or_(Organization.admin_verified == True, Organization.source_type == "SCRAPER_VERIFIED")
            ).all()
            counts = {"colleges": 0, "schools": 0, "hotels": 0, "hospitals": 0, "companies": 0, "it_companies": 0}
            for o in orgs:
                c = classify_org_category(o.category)
                for k in counts:
                    if c.get(k):
                        counts[k] += 1
            print(f"{d:<15}  {counts['colleges']:<8}  {counts['schools']:<8}  {counts['hotels']:<8}  {counts['hospitals']:<9}  {counts['companies']:<9}  {counts['it_companies']:<4}  {len(orgs)}")
        print("-" * 75)

        # Print detailed audit stats
        total_orgs = db.query(func.count(Organization.id)).scalar() or 0
        total_eligible = db.query(func.count(Organization.id)).filter(
            Organization.is_quarantined.isnot(True),
            or_(Organization.admin_verified == True, Organization.source_type == "SCRAPER_VERIFIED")
        ).scalar() or 0
        total_quarantined = db.query(func.count(Organization.id)).filter(Organization.is_quarantined == True).scalar() or 0
        total_admin_verified = db.query(func.count(Organization.id)).filter(Organization.admin_verified == True).scalar() or 0
        total_scraper_verified = db.query(func.count(Organization.id)).filter(
            Organization.admin_verified == False,
            Organization.source_type == "SCRAPER_VERIFIED"
        ).scalar() or 0

        # Duplicate check
        duplicate_count = db.query(
            func.lower(Organization.name),
            func.lower(Organization.district),
            func.count(Organization.id)
        ).group_by(
            func.lower(Organization.name),
            func.lower(Organization.district)
        ).having(func.count(Organization.id) > 1).count()

        print("\nAudit Statistics:")
        print(f"Total Master Organizations:          {total_orgs}")
        print(f"Eligible Verified Organizations:     {total_eligible}")
        print(f"Quarantined Organizations:           {total_quarantined}")
        print(f"Admin Verified:                      {total_admin_verified}")
        print(f"Scraper Verified:                    {total_scraper_verified}")
        print(f"Duplicates:                          {duplicate_count}\n")
    finally:
        db.close()

if __name__ == "__main__":
    print_table()
