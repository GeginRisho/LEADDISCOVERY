import urllib.parse
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Organization, Website, SourcePage
from app.core.cbse_seed_data import TAMIL_NADU_CBSE_SCHOOLS, PUDUCHERRY_CBSE_SCHOOLS

def extract_domain_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc or parsed.path.split("/")[0]
    return netloc.replace("www.", "").lower()

def seed_cbse_schools(db: Session, include_puducherry: bool = False):
    """
    Seeds real CBSE-affiliated schools into PostgreSQL.
    Deduplicates based on CBSE Affiliation Number, normalized Organization Name, and Official Domain.
    Leaves phone/email/social/contact person empty for real crawler extraction.
    """
    datasets = [TAMIL_NADU_CBSE_SCHOOLS]
    if include_puducherry:
        datasets.append(PUDUCHERRY_CBSE_SCHOOLS)

    seeded_org_count = 0
    seeded_web_count = 0
    skipped_count = 0

    for dataset in datasets:
        for item in dataset:
            affiliation = item.get("affiliation_no", "")
            name = item["name"]
            district = item["district"]
            state = item["state"]
            pincode = item.get("pincode", "")
            location = item.get("location", "")
            website_url = item.get("website", "")
            domain = extract_domain_from_url(website_url)

            # Check duplication by Affiliation number in address or exact name + district
            existing_org = None
            all_orgs = db.query(Organization).all()
            for org in all_orgs:
                if affiliation and affiliation in (org.address or ""):
                    existing_org = org
                    break
                if org.name.strip().lower() == name.strip().lower() and (org.city or "").lower() == district.lower():
                    existing_org = org
                    break
                if domain and org.website and org.website.domain == domain:
                    existing_org = org
                    break

            if existing_org:
                skipped_count += 1
                # Ensure website is attached if missing
                if website_url and not existing_org.website:
                    web = Website(
                        organization_id=existing_org.id,
                        domain=domain,
                        url=website_url,
                        status="ACTIVE",
                        discovery_source="SEEDED_OFFICIAL_DIRECTORY",
                        confidence="HIGH"
                    )
                    db.add(web)
                    db.commit()
                    seeded_web_count += 1
                continue

            # Create new Organization record
            address_str = f"{location}, {district}, {state} - {pincode} (CBSE Affiliation No: {affiliation})"
            org = Organization(
                task_id=1, # Default seed reference task
                name=name,
                category="CBSE School",
                address=address_str,
                city=district,
                state=state,
                pincode=pincode,
                confidence="HIGH"
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            seeded_org_count += 1

            # Attach Official Website if verified
            if website_url:
                web = Website(
                    organization_id=org.id,
                    domain=domain,
                    url=website_url,
                    status="ACTIVE",
                    discovery_source="SEEDED_OFFICIAL_DIRECTORY",
                    confidence="HIGH"
                )
                db.add(web)
                db.commit()
                db.refresh(web)
                seeded_web_count += 1

                # Attach CBSE SARAS SourcePage
                source_page = SourcePage(
                    website_id=web.id,
                    url=item.get("saras_url", "https://saras.cbse.gov.in/"),
                    title=f"CBSE SARAS Directory - {name}",
                    status_code=200
                )
                db.add(source_page)
                db.commit()

    return {
        "seeded_org_count": seeded_org_count,
        "seeded_web_count": seeded_web_count,
        "skipped_count": skipped_count
    }

if __name__ == "__main__":
    db = SessionLocal()
    res = seed_cbse_schools(db, include_puducherry=True)
    print(f"Seeding completed: {res}")
    db.close()
