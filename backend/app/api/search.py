import time
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.core.database import get_db
from app.models.models import Organization, OrgBranch, Website, PhoneNumber, EmailAddress, SocialLink
from app.services.location_service import normalize_target_location
from app.services.scraper.identification import normalize_category_and_subcategory

router = APIRouter(prefix="/search", tags=["Fast Search Index"])

@router.get("/fast")
def fast_search_verified_index(
    category: str = Query(..., description="Category (e.g. CBSE school, hotel, college, hospital)"),
    location: str = Query(..., description="Target Location (e.g. Erode, Puducherry, Kanyakumari, Salem, Chennai)"),
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Dedicated Fast Verified Search Read Path.
    Queries Master Organizations and OrgBranches using composite SQL indexes.
    Target response time: < 3 seconds total (< 500ms database query time).
    Never executes live web scraping synchronously.
    Returns ONLY verified (Admin-verified or 7-flag Scraper-verified) master organizations/branches.
    """
    request_started = time.time()
    iso_started = datetime.datetime.utcnow().isoformat()

    # 1. Normalize Category & Location
    norm_cat, norm_subcat = normalize_category_and_subcategory(category)
    target_loc = normalize_target_location(location)

    database_query_started = time.time()

    # Base Filter: Category & Subcategory matching
    cat_filter = [Organization.category == norm_cat]
    if norm_subcat and norm_subcat != norm_cat:
        cat_filter.append(Organization.sub_category == norm_subcat)

    # Verification Filter: (Admin Verified) OR (7-Flag Scraper Verified with HIGH confidence)
    scraper_verified_clause = and_(
        Organization.identity_verified == True,
        Organization.category_verified == True,
        Organization.country_verified == True,
        Organization.state_verified == True,
        Organization.district_verified == True,
        Organization.location_verified == True,
        Organization.official_website_verified == True,
        Organization.confidence == "HIGH"
    )
    verification_clause = or_(
        Organization.admin_verified == True,
        scraper_verified_clause
    )

    # Quarantine Filter: Exclude quarantined non-organization portal records
    quarantine_clause = or_(Organization.is_quarantined == False, Organization.is_quarantined.is_(None))

    # Main Query with Branches Eager Loading
    query = db.query(Organization).options(
        joinedload(Organization.website),
        joinedload(Organization.phone_numbers),
        joinedload(Organization.email_addresses),
        joinedload(Organization.social_links),
        joinedload(Organization.branches)
    ).filter(
        *cat_filter,
        verification_clause,
        quarantine_clause
    )

    # Location Filter: Match HQ OR Branch
    target_dist = target_loc["target_district"]
    target_state = target_loc["target_state_or_ut"]

    if target_dist:
        hq_loc_match = (Organization.district == target_dist)
        branch_loc_match = Organization.branches.any(OrgBranch.district == target_dist)
        query = query.filter(or_(hq_loc_match, branch_loc_match))
    elif target_state:
        hq_loc_match = (Organization.state == target_state)
        branch_loc_match = Organization.branches.any(OrgBranch.state == target_state)
        query = query.filter(or_(hq_loc_match, branch_loc_match))

    organizations = query.limit(limit * 2).all()

    database_query_finished = time.time()
    db_execution_ms = round((database_query_finished - database_query_started) * 1000, 2)

    results = []
    seen_keys = set()

    for org in organizations:
        if len(results) >= limit:
            break

        # Check HQ qualification
        hq_qualifies = True
        if target_dist and org.district != target_dist:
            hq_qualifies = False
        elif target_state and org.state != target_state:
            hq_qualifies = False

        if hq_qualifies:
            key = f"org_{org.id}_hq"
            if key not in seen_keys:
                seen_keys.add(key)
                results.append({
                    "id": org.id,
                    "branch_id": None,
                    "name": org.display_name or org.name,
                    "organization_name": org.name,
                    "category": org.category,
                    "sub_category": org.sub_category,
                    "official_website_url": org.official_website_url,
                    "google_maps_url": org.google_maps_url,
                    "address": org.address,
                    "city": org.city,
                    "district": org.district,
                    "state": org.state,
                    "country": org.country,
                    "pincode": org.pincode,
                    "confidence": org.confidence,
                    "source_type": org.source_type or ("ADMIN_VERIFIED" if org.admin_verified else "SCRAPER_VERIFIED"),
                    "verification_badge": "ADMIN VERIFIED" if org.admin_verified else "WEB VERIFIED",
                    "admin_verified": org.admin_verified,
                    "verified_by": org.verified_by,
                    "verified_at": org.verified_at.isoformat() if org.verified_at else None,
                    "identity_verified": org.identity_verified,
                    "category_verified": org.category_verified,
                    "country_verified": org.country_verified,
                    "state_verified": org.state_verified,
                    "district_verified": org.district_verified,
                    "location_verified": org.location_verified,
                    "official_website_verified": org.official_website_verified,
                    "website": {"url": org.website.url, "domain": org.website.domain} if org.website else None,
                    "phones": [{"raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type} for p in org.phone_numbers],
                    "emails": [{"email": e.email} for e in org.email_addresses],
                    "socials": [
                        {"platform": "facebook", "url": org.facebook_url} if org.facebook_url else None,
                        {"platform": "instagram", "url": org.instagram_url} if org.instagram_url else None,
                        {"platform": "linkedin", "url": org.linkedin_url} if org.linkedin_url else None,
                        {"platform": "youtube", "url": org.youtube_url} if org.youtube_url else None,
                        {"platform": "x", "url": org.x_url} if org.x_url else None,
                        {"platform": "whatsapp", "url": org.whatsapp_url} if org.whatsapp_url else None,
                    ] + [{"platform": s.platform, "url": s.url} for s in org.social_links],
                    "other_links": org.other_links or []
                })

        # Check Branches qualification
        for branch in org.branches:
            if len(results) >= limit:
                break
            branch_qualifies = True
            if target_dist and branch.district != target_dist:
                branch_qualifies = False
            elif target_state and branch.state != target_state:
                branch_qualifies = False

            if branch_qualifies:
                key = f"org_{org.id}_branch_{branch.id}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append({
                        "id": org.id,
                        "branch_id": branch.id,
                        "name": f"{org.name} ({branch.branch_name})",
                        "organization_name": org.name,
                        "branch_name": branch.branch_name,
                        "category": org.category,
                        "sub_category": org.sub_category,
                        "official_website_url": branch.website_url or org.official_website_url,
                        "google_maps_url": branch.maps_url or org.google_maps_url,
                        "address": branch.address or org.address,
                        "city": branch.city or org.city,
                        "district": branch.district,
                        "state": branch.state,
                        "country": branch.country,
                        "pincode": branch.pincode or org.pincode,
                        "confidence": org.confidence,
                        "source_type": org.source_type or ("ADMIN_VERIFIED" if org.admin_verified else "SCRAPER_VERIFIED"),
                        "verification_badge": "ADMIN VERIFIED" if org.admin_verified else "WEB VERIFIED",
                        "provenance_badge": "ADMIN VERIFIED" if org.admin_verified else "WEB VERIFIED",
                        "admin_verified": org.admin_verified,
                        "verified_by": org.verified_by,
                        "verified_at": org.verified_at.isoformat() if org.verified_at else None,
                        "identity_verified": org.identity_verified,
                        "category_verified": org.category_verified,
                        "country_verified": org.country_verified,
                        "state_verified": org.state_verified,
                        "district_verified": org.district_verified,
                        "location_verified": org.location_verified,
                        "official_website_verified": org.official_website_verified,
                        "website": {"url": branch.website_url or (org.website.url if org.website else None)},
                        "phones": branch.phone_numbers or [{"raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type} for p in org.phone_numbers],
                        "emails": branch.email_addresses or [{"email": e.email} for e in org.email_addresses],
                        "socials": [],
                        "other_links": org.other_links or []
                    })

    response_sent = time.time()
    total_response_ms = round((response_sent - request_started) * 1000, 2)

    # Performance Log
    print(
        f"[FAST VERIFIED SEARCH LOG] "
        f"request_started={iso_started} | "
        f"category='{category}' (norm='{norm_cat}'/'{norm_subcat}') | "
        f"location='{location}' (district='{target_loc['target_district']}') | "
        f"results={len(results)} | "
        f"db_query_time={db_execution_ms}ms | "
        f"total_response_time={total_response_ms}ms"
    )

    return {
        "status": "SUCCESS",
        "category": category,
        "location": location,
        "normalized_category": norm_cat,
        "normalized_subcategory": norm_subcat,
        "target_district": target_loc["target_district"],
        "target_state": target_loc["target_state_or_ut"],
        "count": len(results),
        "timings": {
            "request_started": iso_started,
            "database_query_ms": db_execution_ms,
            "total_response_ms": total_response_ms
        },
        "results": results
    }
