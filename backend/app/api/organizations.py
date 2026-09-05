import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.models.models import (
    Organization, Website, PhoneNumber, EmailAddress, SocialLink, District
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.get("/stats")
def get_organization_stats(db: Session = Depends(get_db)):
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_orgs = db.query(func.count(Organization.id)).scalar() or 0
    new_today = db.query(func.count(Organization.id)).filter(Organization.created_at >= today_start).scalar() or 0
    updated_today = db.query(func.count(Organization.id)).filter(Organization.updated_at >= today_start).scalar() or 0
    verified_websites = db.query(func.count(Website.id)).filter(Website.status == "ACTIVE").scalar() or 0
    total_phones = db.query(func.count(PhoneNumber.id)).scalar() or 0
    total_emails = db.query(func.count(EmailAddress.id)).scalar() or 0

    return {
        "total_organizations": total_orgs,
        "new_today": new_today,
        "updated_today": updated_today,
        "verified_websites": verified_websites,
        "total_phones": total_phones,
        "total_emails": total_emails
    }

@router.get("/districts")
def get_district_breakdown(db: Session = Depends(get_db)):
    districts = db.query(District).order_by(District.district_name.asc()).all()
    result = []

    for dist in districts:
        d_name = dist.district_name
        d_filter = func.lower(Organization.district) == d_name.lower()

        total_orgs = db.query(func.count(Organization.id)).filter(d_filter).scalar() or 0
        colleges = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%college%")).scalar() or 0
        hotels = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%hotel%")).scalar() or 0
        hospitals = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%hospital%")).scalar() or 0
        companies = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%company%")).scalar() or 0
        it_companies = db.query(func.count(Organization.id)).filter(d_filter, or_(func.lower(Organization.category).like("%it%"), func.lower(Organization.category).like("%software%"))).scalar() or 0
        schools = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%school%")).scalar() or 0

        result.append({
            "district_id": dist.id,
            "district_name": dist.district_name,
            "state": dist.state,
            "country": dist.country,
            "official_district_url": dist.official_district_url,
            "total_organizations": total_orgs,
            "colleges_count": colleges,
            "hotels_count": hotels,
            "hospitals_count": hospitals,
            "companies_count": companies,
            "it_companies_count": it_companies,
            "schools_count": schools
        })

    return result

@router.get("")
def list_organizations(
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    confidence: Optional[str] = Query(None),
    website_verified: Optional[bool] = Query(None),
    phone_available: Optional[bool] = Query(None),
    email_available: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Organization)

    if district and district.upper() != "ALL":
        query = query.filter(func.lower(Organization.district) == district.strip().lower())

    if category and category.upper() != "ALL":
        query = query.filter(func.lower(Organization.category).like(f"%{category.strip().lower()}%"))

    if city and city.strip():
        query = query.filter(func.lower(Organization.city).like(f"%{city.strip().lower()}%"))

    if state and state.strip() and state.upper() != "ALL":
        query = query.filter(func.lower(Organization.state).like(f"%{state.strip().lower()}%"))

    if confidence and confidence.upper() != "ALL":
        query = query.filter(Organization.confidence == confidence.upper())

    if website_verified is True:
        query = query.join(Website).filter(Website.status == "ACTIVE", Website.url.isnot(None))
    elif website_verified is False:
        query = query.outerjoin(Website).filter(or_(Website.id.is_(None), Website.status != "ACTIVE", Website.url.is_(None)))

    if phone_available is True:
        query = query.filter(Organization.phone_numbers.any())
    elif phone_available is False:
        query = query.filter(~Organization.phone_numbers.any())

    if email_available is True:
        query = query.filter(Organization.email_addresses.any())
    elif email_available is False:
        query = query.filter(~Organization.email_addresses.any())

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Organization.name).like(s),
                func.lower(Organization.category).like(s),
                func.lower(Organization.city).like(s),
                func.lower(Organization.district).like(s)
            )
        )

    total = query.count()
    offset = (page - 1) * limit
    orgs = query.order_by(Organization.updated_at.desc()).offset(offset).limit(limit).all()

    items = []
    for o in orgs:
        web_info = None
        if o.website:
            web_info = {
                "domain": o.website.domain,
                "url": o.website.url,
                "status": o.website.status,
                "reason": o.website.reason,
                "verified": o.website.status == "ACTIVE" and bool(o.website.url)
            }

        phones = [{"raw": p.raw_value, "normalized": p.normalized_value, "type": p.type} for p in o.phone_numbers]
        emails = [{"email": e.email, "extraction_method": e.extraction_method} for e in o.email_addresses]
        socials = [{"platform": s.platform, "url": s.url} for s in o.social_links]

        items.append({
            "id": o.id,
            "name": o.name,
            "category": o.category,
            "address": o.address,
            "city": o.city,
            "district": o.district,
            "state": o.state,
            "pincode": o.pincode,
            "confidence": o.confidence,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            "website": web_info,
            "phones": phones,
            "emails": emails,
            "socials": socials
        })

    pages = (total + limit - 1) // limit if limit > 0 else 1

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "organizations": items
    }

@router.get("/matrix")
def get_campaign_matrix(db: Session = Depends(get_db)):
    from app.core.tn_districts import ALL_REGIONS
    matrix = []

    for reg in ALL_REGIONS:
        r_name = reg["name"]
        d_filter = func.lower(Organization.district) == r_name.lower()

        total = db.query(func.count(Organization.id)).filter(d_filter).scalar() or 0
        colleges = db.query(func.count(Organization.id)).filter(d_filter, or_(func.lower(Organization.category).like("%college%"), func.lower(Organization.category).like("%university%"))).scalar() or 0
        schools = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%school%")).scalar() or 0
        hotels = db.query(func.count(Organization.id)).filter(d_filter, or_(func.lower(Organization.category).like("%hotel%"), func.lower(Organization.category).like("%resort%"))).scalar() or 0
        hospitals = db.query(func.count(Organization.id)).filter(d_filter, or_(func.lower(Organization.category).like("%hospital%"), func.lower(Organization.category).like("%clinic%"))).scalar() or 0
        companies = db.query(func.count(Organization.id)).filter(d_filter, func.lower(Organization.category).like("%company%")).scalar() or 0
        it_companies = db.query(func.count(Organization.id)).filter(d_filter, or_(func.lower(Organization.category).like("%it%"), func.lower(Organization.category).like("%software%"), func.lower(Organization.category).like("%tech%"))).scalar() or 0

        matrix.append({
            "region": r_name,
            "colleges": colleges,
            "schools": schools,
            "hotels": hotels,
            "hospitals": hospitals,
            "companies": companies,
            "it_companies": it_companies,
            "total": total
        })

    return matrix

@router.post("/manual", status_code=201)
def create_organization_manual(
    payload: dict,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_user)
):
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "").strip()
    district = (payload.get("district") or payload.get("region") or "").strip()

    if not name or not category or not district:
        raise HTTPException(status_code=400, detail="Organization Name, Category, and District/Region are required.")

    website_url = (payload.get("website") or payload.get("official_website") or "").strip()
    phone_val = (payload.get("phone") or "").strip()
    email_val = (payload.get("email") or "").strip()
    city_val = (payload.get("city") or "").strip()

    # Verify manual website before marking verified
    is_web_verified = False
    domain = ""
    if website_url:
        from app.services.scraper.identification import identify_official_website, extract_domain
        web_eval = identify_official_website(name, website_url)
        domain = extract_domain(website_url)
        if web_eval.get("is_official") and not web_eval.get("is_directory_source"):
            is_web_verified = True

    # Pre-insertion duplicate check
    existing = None
    if domain:
        web_match = db.query(Website).filter(Website.domain == domain).first()
        if web_match and web_match.organization:
            existing = web_match.organization

    if not existing and phone_val:
        p_match = db.query(PhoneNumber).filter(PhoneNumber.normalized_value == phone_val).first()
        if p_match and p_match.organization:
            existing = p_match.organization

    if not existing and email_val:
        e_match = db.query(EmailAddress).filter(EmailAddress.email == email_val.lower()).first()
        if e_match and e_match.organization:
            existing = e_match.organization

    if not existing:
        exact_match = db.query(Organization).filter(
            func.lower(Organization.name) == name.lower(),
            func.lower(Organization.district) == district.lower()
        ).first()
        if exact_match:
            existing = exact_match

    if existing:
        raise HTTPException(status_code=400, detail=f"Organization already exists (ID: {existing.id}, Name: '{existing.name}'). Duplicate record creation blocked.")

    state_val = "Puducherry UT" if district.lower() == "puducherry" else "Tamil Nadu"

    # Create Organization
    org = Organization(
        name=name,
        category=category,
        district=district,
        city=city_val or district,
        state=state_val,
        address=payload.get("address"),
        pincode=payload.get("pincode"),
        confidence="HIGH" if (is_web_verified and (phone_val or email_val)) else ("MEDIUM" if is_web_verified else "LOW"),
        source_type="MANUAL"
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Attach Website with explicit verification status
    if website_url:
        web = Website(
            organization_id=org.id,
            domain=domain or website_url,
            url=website_url,
            status="ACTIVE" if is_web_verified else "UNVERIFIED",
            reason="Verified manual entry" if is_web_verified else "Domain on directory/blacklisted portal",
            discovery_source="MANUAL_ENTRY",
            confidence=org.confidence
        )
        db.add(web)

    # Attach Phone
    if phone_val:
        p_obj = PhoneNumber(
            organization_id=org.id,
            raw_value=phone_val,
            normalized_value=phone_val,
            type="main"
        )
        db.add(p_obj)

    # Attach Email
    if email_val:
        e_obj = EmailAddress(
            organization_id=org.id,
            email=email_val.lower(),
            extraction_method="MANUAL_ENTRY"
        )
        db.add(e_obj)

    db.commit()
    db.refresh(org)
    return {"message": f"Organization '{org.name}' added successfully.", "id": org.id}

@router.put("/{org_id}")
def update_organization(
    org_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if "name" in payload and payload["name"].strip():
        org.name = payload["name"].strip()
    if "category" in payload:
        org.category = payload["category"].strip()
    if "district" in payload:
        org.district = payload["district"].strip()
    if "city" in payload:
        org.city = payload["city"].strip()
    if "address" in payload:
        org.address = payload["address"].strip()
    if "confidence" in payload:
        org.confidence = payload["confidence"].strip()

    org.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": f"Organization ID {org.id} updated successfully."}

@router.delete("/{org_id}")
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    db.delete(org)
    db.commit()
    return {"message": f"Organization ID {org_id} deleted."}

@router.post("/{org_id}/verify")
def verify_organization(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user = Depends(get_current_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    org.confidence = "HIGH"
    org.last_verified_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": f"Organization '{org.name}' verified successfully."}

