import sys
import os

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.engine.url import make_url
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Organization
from app.core.tn_districts import ALL_REGIONS, normalize_district
from app.api.organizations import _query_eligible_matrix_counts

def audit_database():
    db_url_parsed = make_url(settings.DATABASE_URL)
    db_host = db_url_parsed.host or "localhost"
    db_name = db_url_parsed.database or "leaddiscovery"

    db: Session = SessionLocal()
    try:
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

        counts_map = _query_eligible_matrix_counts(db)

        header = f"{'District / Region':<20} | {'Colleges':<8} | {'Schools':<8} | {'Hotels':<8} | {'Hospitals':<8} | {'Companies':<9} | {'IT Companies':<12} | {'Total'}"
        divider = "-" * len(header)

        print("\n=========================================================================")
        print(f"       POSTGRESQL MASTER DATABASE AUDIT (Host: {db_host} | DB: {db_name})       ")
        print("=========================================================================\n")
        print(header)
        print(divider)

        total_matrix_sum = 0
        for reg in ALL_REGIONS:
            r_name = reg["name"]
            d_key = r_name.lower()
            c = counts_map.get(d_key, {"total": 0, "colleges": 0, "schools": 0, "hotels": 0, "hospitals": 0, "companies": 0, "it_companies": 0})
            total_matrix_sum += c["total"]
            print(f"{r_name:<20} | {c['colleges']:<8} | {c['schools']:<8} | {c['hotels']:<8} | {c['hospitals']:<8} | {c['companies']:<9} | {c['it_companies']:<12} | {c['total']}")

        # Check potential duplicates by (lower(name), lower(district))
        duplicate_count = db.query(
            func.lower(Organization.name),
            func.lower(Organization.district),
            func.count(Organization.id)
        ).group_by(
            func.lower(Organization.name),
            func.lower(Organization.district)
        ).having(func.count(Organization.id) > 1).count()

        populated_regions = sum(1 for reg in ALL_REGIONS if counts_map.get(reg["name"].lower(), {}).get("total", 0) > 0)
        empty_regions = len(ALL_REGIONS) - populated_regions

        cat_totals = {"colleges": 0, "schools": 0, "hotels": 0, "hospitals": 0, "companies": 0, "it_companies": 0}
        for reg in ALL_REGIONS:
            c = counts_map.get(reg["name"].lower(), {})
            for k in cat_totals:
                cat_totals[k] += c.get(k, 0)

        print(divider)
        print(f"\n--- DATABASE AUDIT SUMMARY ---")
        print(f"Database Host:                      {db_host}")
        print(f"Database Name:                      {db_name}")
        print(f"Total Regional Matrix Rows:         {len(ALL_REGIONS)} (38 TN + 1 Puducherry UT)")
        print(f"Populated Regions:                  {populated_regions}")
        print(f"Empty Regions:                      {empty_regions}")
        print(f"Total Master Organizations:          {total_orgs}")
        print(f"Total Eligible Verified Orgs:        {total_eligible}")
        print(f"Total Quarantined Organizations:     {total_quarantined}")
        print(f"Total Admin Verified Organizations:  {total_admin_verified}")
        print(f"Total Scraper Verified Orgs:         {total_scraper_verified}")
        print(f"Total Duplicates Detected:           {duplicate_count}")
        print(f"Sum of Regional Matrix Totals:       {total_matrix_sum}")
        print(f"\nPer-Category Matrix Totals:")
        print(f"  Colleges:     {cat_totals['colleges']}")
        print(f"  Schools:      {cat_totals['schools']}")
        print(f"  Hotels:       {cat_totals['hotels']}")
        print(f"  Hospitals:    {cat_totals['hospitals']}")
        print(f"  Companies:    {cat_totals['companies']}")
        print(f"  IT Companies: {cat_totals['it_companies']}")
        print("=========================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    audit_database()
