import time
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.models import Organization, Website, PhoneNumber, EmailAddress, SocialLink
from app.schemas.leads import OrganizationLeadResponse
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
    Queries Master Organizations database using composite SQL indexes.
    Target response time: < 3 seconds total (< 500ms database query time).
    Never executes live web scraping synchronously.
    Returns ONLY 100% verified, HIGH confidence master organizations.
    """
    request_started = time.time()
    iso_started = datetime.datetime.utcnow().isoformat()

    # 1. Normalize Category & Location
    norm_cat, norm_subcat = normalize_category_and_subcategory(category)
    target_loc = normalize_target_location(location)

    database_query_started = time.time()

    # 2. Build Fast Index Query
    query = db.query(Organization).options(
        joinedload(Organization.website),
        joinedload(Organization.phone_numbers),
        joinedload(Organization.email_addresses),
        joinedload(Organization.social_links)
    ).filter(
        Organization.category == norm_cat,
        Organization.identity_verified == True,
        Organization.category_verified == True,
        Organization.country_verified == True,
        Organization.state_verified == True,
        Organization.district_verified == True,
        Organization.location_verified == True,
        Organization.official_website_verified == True,
        Organization.confidence == "HIGH"
    )

    # Subcategory filter if query specifically implies subcategory (e.g. CBSE)
    if norm_subcat and norm_subcat != norm_cat:
        query = query.filter(Organization.sub_category == norm_subcat)

    # Strict location filter (District & State/UT)
    if target_loc["target_district"]:
        query = query.filter(Organization.district == target_loc["target_district"])
    if target_loc["target_state_or_ut"]:
        query = query.filter(Organization.state == target_loc["target_state_or_ut"])

    # Execute DB query
    organizations = query.limit(limit).all()

    database_query_finished = time.time()
    db_execution_ms = round((database_query_finished - database_query_started) * 1000, 2)

    # Format output items
    results = []
    for org in organizations:
        results.append({
            "id": org.id,
            "name": org.name,
            "category": org.category,
            "sub_category": org.sub_category,
            "official_website_url": org.official_website_url,
            "address": org.address,
            "city": org.city,
            "district": org.district,
            "state": org.state,
            "country": org.country,
            "pincode": org.pincode,
            "confidence": org.confidence,
            "identity_verified": org.identity_verified,
            "category_verified": org.category_verified,
            "country_verified": org.country_verified,
            "state_verified": org.state_verified,
            "district_verified": org.district_verified,
            "location_verified": org.location_verified,
            "official_website_verified": org.official_website_verified,
            "website": {"url": org.website.url, "domain": org.website.domain} if org.website else None,
            "phones": [{"raw_value": p.raw_value, "normalized_value": p.normalized_value} for p in org.phone_numbers],
            "emails": [{"email": e.email} for e in org.email_addresses],
            "socials": [{"platform": s.platform, "url": s.url} for s in org.social_links]
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
