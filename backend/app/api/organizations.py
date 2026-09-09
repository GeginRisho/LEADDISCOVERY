import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.models.models import (
    Organization, Website, PhoneNumber, EmailAddress, SocialLink, District, User
)
from app.api.auth import get_current_user, get_current_admin_user

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.get("/stats")
def get_organization_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
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

def classify_org_category(cat: Optional[str]) -> Dict[str, bool]:
    cat_lower = (cat or "").lower().strip()
    is_it = "it company" in cat_lower or "software" in cat_lower or "tech" in cat_lower or "information technology" in cat_lower
    is_college = "college" in cat_lower or "university" in cat_lower or "higher education" in cat_lower
    is_school = "school" in cat_lower or "cbse" in cat_lower or "matriculation" in cat_lower or "academy" in cat_lower
    is_hotel = "hotel" in cat_lower or "resort" in cat_lower or "lodging" in cat_lower or "hospitality" in cat_lower
    is_hospital = "hospital" in cat_lower or "clinic" in cat_lower or "healthcare" in cat_lower or "medical" in cat_lower
    is_comp = not is_it and ("company" in cat_lower or "corporate" in cat_lower or "business" in cat_lower or "enterprise" in cat_lower)

    return {
        "colleges": is_college,
        "schools": is_school,
        "hotels": is_hotel,
        "hospitals": is_hospital,
        "it_companies": is_it,
        "companies": is_comp
    }

def _query_eligible_matrix_counts(db: Session):
    from app.core.tn_districts import normalize_district
    
    counts_query = db.query(
        Organization.district,
        Organization.category,
        func.count(Organization.id).label("count")
    ).filter(
        Organization.is_quarantined.isnot(True),
        or_(
            Organization.admin_verified == True,
            Organization.source_type == "SCRAPER_VERIFIED"
        )
    ).group_by(
        Organization.district,
        Organization.category
    ).all()

    counts_map = {}
    for d_name, cat, count in counts_query:
        if not d_name:
            continue
        canon_dist = normalize_district(d_name)
        d_key = canon_dist.lower()
        if d_key not in counts_map:
            counts_map[d_key] = {"total": 0, "colleges": 0, "hotels": 0, "hospitals": 0, "companies": 0, "it_companies": 0, "schools": 0}

        counts_map[d_key]["total"] += count
        cats = classify_org_category(cat)

        if cats["colleges"]:
            counts_map[d_key]["colleges"] += count
        if cats["schools"]:
            counts_map[d_key]["schools"] += count
        if cats["hotels"]:
            counts_map[d_key]["hotels"] += count
        if cats["hospitals"]:
            counts_map[d_key]["hospitals"] += count
        if cats["it_companies"]:
            counts_map[d_key]["it_companies"] += count
        if cats["companies"]:
            counts_map[d_key]["companies"] += count

    return counts_map

@router.get("/districts")
def get_district_breakdown(db: Session = Depends(get_db)):
    districts = db.query(District).order_by(District.district_name.asc()).all()
    counts_map = _query_eligible_matrix_counts(db)

    result = []
    for dist in districts:
        d_key = dist.district_name.strip().lower()
        d_counts = counts_map.get(d_key, {"total": 0, "colleges": 0, "hotels": 0, "hospitals": 0, "companies": 0, "it_companies": 0, "schools": 0})
        result.append({
            "district_id": dist.id,
            "district_name": dist.district_name,
            "state": dist.state,
            "country": dist.country,
            "official_district_url": dist.official_district_url,
            "total_organizations": d_counts["total"],
            "colleges_count": d_counts["colleges"],
            "hotels_count": d_counts["hotels"],
            "hospitals_count": d_counts["hospitals"],
            "companies_count": d_counts["companies"],
            "it_companies_count": d_counts["it_companies"],
            "schools_count": d_counts["schools"]
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
    verification_status: Optional[str] = Query(None),
    website_verified: Optional[bool] = Query(None),
    phone_available: Optional[bool] = Query(None),
    email_available: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    query = db.query(Organization)

    if district and district.upper() != "ALL":
        query = query.filter(func.lower(Organization.district) == district.strip().lower())

    if category and category.upper() != "ALL":
        query = query.filter(func.lower(Organization.category).like(f"%{category.strip().lower()}%"))

    if city and city.strip() and city.upper() != "ALL":
        query = query.filter(func.lower(Organization.city).like(f"%{city.strip().lower()}%"))

    if state and state.strip() and state.upper() != "ALL":
        query = query.filter(func.lower(Organization.state).like(f"%{state.strip().lower()}%"))

    if country and country.strip() and country.upper() != "ALL":
        query = query.filter(func.lower(Organization.country) == country.strip().lower())

    if confidence and confidence.upper() != "ALL":
        query = query.filter(Organization.confidence == confidence.upper())

    if verification_status and verification_status.upper() != "ALL":
        v = verification_status.upper()
        if v == "ADMIN_VERIFIED":
            query = query.filter(Organization.admin_verified == True)
        elif v == "SCRAPER_VERIFIED":
            query = query.filter(Organization.admin_verified == False, Organization.source_type == "SCRAPER_VERIFIED")
        elif v == "UNVERIFIED":
            query = query.filter(Organization.admin_verified == False)
        elif v == "QUARANTINED":
            query = query.filter(Organization.is_quarantined == True)

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
    orgs = (
        query.options(
            selectinload(Organization.website),
            selectinload(Organization.phone_numbers),
            selectinload(Organization.email_addresses),
            selectinload(Organization.social_links),
            selectinload(Organization.branches),
        )
        .order_by(Organization.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

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

        branches_data = []
        if o.branches:
            for b in o.branches:
                branches_data.append({
                    "id": b.id,
                    "branch_name": b.branch_name,
                    "country": b.country,
                    "state": b.state,
                    "district": b.district,
                    "city": b.city,
                    "address": b.address,
                    "pincode": b.pincode,
                    "phone_numbers": b.phone_numbers,
                    "email_addresses": b.email_addresses,
                    "website_url": b.website_url,
                    "maps_url": b.maps_url
                })

        items.append({
            "id": o.id,
            "name": o.name,
            "display_name": o.display_name,
            "category": o.category,
            "sub_category": o.sub_category,
            "description": o.description,
            "address": o.address,
            "city": o.city,
            "district": o.district,
            "state": o.state,
            "country": o.country,
            "pincode": o.pincode,
            "confidence": o.confidence,
            "admin_verified": o.admin_verified,
            "verified_by": o.verified_by,
            "verified_at": o.verified_at.isoformat() if o.verified_at else None,
            "verification_method": o.verification_method,
            "source_type": o.source_type,
            "previous_source_type": o.previous_source_type,
            "is_quarantined": o.is_quarantined,
            "quarantine_reason": o.quarantine_reason,
            "official_website_url": o.official_website_url,
            "google_maps_url": o.google_maps_url,
            "facebook_url": o.facebook_url,
            "instagram_url": o.instagram_url,
            "linkedin_url": o.linkedin_url,
            "youtube_url": o.youtube_url,
            "x_url": o.x_url,
            "whatsapp_url": o.whatsapp_url,
            "other_links": o.other_links or [],
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            "website": web_info,
            "phones": phones,
            "emails": emails,
            "socials": socials,
            "branches": branches_data
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
def get_campaign_matrix(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    from app.core.tn_districts import ALL_REGIONS
    
    counts_map = _query_eligible_matrix_counts(db)

    matrix = []
    for reg in ALL_REGIONS:
        r_name = reg["name"]
        r_counts = counts_map.get(r_name.lower(), {"total": 0, "colleges": 0, "schools": 0, "hotels": 0, "hospitals": 0, "companies": 0, "it_companies": 0})
        matrix.append({
            "region": r_name,
            "colleges": r_counts["colleges"],
            "colleges_target": 32,
            "schools": r_counts["schools"],
            "schools_target": 23,
            "hotels": r_counts["hotels"],
            "hotels_target": 50,
            "hospitals": r_counts["hospitals"],
            "hospitals_target": 20,
            "companies": r_counts["companies"],
            "companies_target": 24,
            "it_companies": r_counts["it_companies"],
            "it_companies_target": 28,
            "total": r_counts["total"],
            "total_target": 177
        })

    return matrix

@router.post("/manual", status_code=201)
def create_organization_manual(
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    from app.core.tn_districts import normalize_district
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "").strip()
    raw_district = (payload.get("district") or payload.get("region") or "").strip()
    district = normalize_district(raw_district)

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
        existing_web = db.query(Website).filter(Website.organization_id == org.id).first()
        if existing_web:
            existing_web.domain = domain or website_url
            existing_web.url = website_url
            existing_web.status = "ACTIVE" if is_web_verified else "UNVERIFIED"
            existing_web.reason = "Verified manual entry" if is_web_verified else "Domain on directory/blacklisted portal"
            existing_web.discovery_source = "MANUAL_ENTRY"
            existing_web.confidence = org.confidence
        else:
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
    admin_user: User = Depends(get_current_admin_user)
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
    admin_user: User = Depends(get_current_admin_user)
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
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if not org.admin_verified:
        org.previous_source_type = org.source_type or "SCRAPER_VERIFIED"
        org.admin_verified = True
        org.source_type = "ADMIN_VERIFIED"
        org.verification_method = "ADMIN"
        org.verified_by = admin_user.email
        org.verified_at = datetime.datetime.utcnow()
        org.confidence = "HIGH"
        org.last_verified_at = datetime.datetime.utcnow()
        org.updated_at = datetime.datetime.utcnow()
        db.commit()

    return {
        "message": f"Organization '{org.name}' verified successfully.",
        "id": org.id,
        "admin_verified": True,
        "source_type": org.source_type,
        "verified_by": org.verified_by
    }

@router.post("/{org_id}/unverify")
def unverify_organization(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if org.admin_verified:
        org.admin_verified = False
        org.source_type = org.previous_source_type or ("MANUAL" if org.verification_method == "ADMIN" else "SCRAPER_VERIFIED")
        org.verified_by = None
        org.verified_at = None
        org.updated_at = datetime.datetime.utcnow()
        db.commit()

    return {
        "message": f"Organization '{org.name}' unverified successfully.",
        "id": org.id,
        "admin_verified": False,
        "source_type": org.source_type
    }

