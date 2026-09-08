from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, case
from typing import List, Optional
import datetime

from app.core.database import get_db
from app.models.models import (
    User, ScrapingTask, Organization, Website, 
    PhoneNumber, EmailAddress, SocialLink, ScrapingLog, District,
    TaskLead, OrgBranch
)
from app.schemas.auth import UserResponse
from app.schemas.tasks import ScrapingTaskResponse, ScrapingLogResponse
from app.api.auth import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    # 1. Aggregate User Metrics in 1 Query
    user_row = db.query(
        func.count(User.id).label("total"),
        func.sum(case((User.role == "ADMIN", 1), else_=0)).label("admins"),
        func.sum(case((User.role == "USER", 1), else_=0)).label("normal"),
        func.sum(case((User.status == "ACTIVE", 1), else_=0)).label("active"),
        func.sum(case((User.status == "SUSPENDED", 1), else_=0)).label("suspended")
    ).first()

    # 2. Aggregate Task Metrics in 1 Query
    task_row = db.query(
        func.count(ScrapingTask.id).label("total"),
        func.sum(case((ScrapingTask.status == "RUNNING", 1), else_=0)).label("running"),
        func.sum(case((ScrapingTask.status == "COMPLETED", 1), else_=0)).label("completed"),
        func.sum(case((ScrapingTask.status == "FAILED", 1), else_=0)).label("failed"),
        func.coalesce(func.sum(ScrapingTask.discovered_count), 0).label("discovered"),
        func.coalesce(func.sum(ScrapingTask.websites_found), 0).label("websites_found"),
        func.coalesce(func.sum(ScrapingTask.websites_crawled), 0).label("websites_crawled"),
        func.coalesce(func.sum(ScrapingTask.failed_count), 0).label("failed_crawls")
    ).first()

    # 3. Aggregate Entities Count
    total_leads = db.query(func.count(Organization.id)).scalar() or 0
    total_emails = db.query(func.count(EmailAddress.id)).scalar() or 0
    total_phones = db.query(func.count(PhoneNumber.id)).scalar() or 0
    total_socials = db.query(func.count(SocialLink.id)).scalar() or 0

    return {
        "total_users": int(user_row.total or 0),
        "total_admins": int(user_row.admins or 0),
        "total_normal_users": int(user_row.normal or 0),
        "active_users": int(user_row.active or 0),
        "suspended_users": int(user_row.suspended or 0),
        "total_tasks": int(task_row.total or 0),
        "running_tasks": int(task_row.running or 0),
        "completed_tasks": int(task_row.completed or 0),
        "failed_tasks": int(task_row.failed or 0),
        "total_discovered": int(task_row.discovered or 0),
        "total_websites_found": int(task_row.websites_found or 0),
        "total_websites_crawled": int(task_row.websites_crawled or 0),
        "total_failed_crawls": int(task_row.failed_crawls or 0),
        "total_leads": int(total_leads),
        "total_emails": int(total_emails),
        "total_phones": int(total_phones),
        "total_socials": int(total_socials)
    }

@router.get("/data-diagnostics")
def get_data_diagnostics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    from app.core.database import engine
    url = engine.url
    return {
        "database": {
            "driver": url.drivername,
            "host": url.host or "localhost",
            "database_name": url.database,
            "user": url.username
        },
        "counts": {
            "users": db.query(func.count(User.id)).scalar() or 0,
            "admins": db.query(func.count(User.id)).filter(User.role == "ADMIN").scalar() or 0,
            "normal_users": db.query(func.count(User.id)).filter(User.role == "USER").scalar() or 0,
            "active_users": db.query(func.count(User.id)).filter(User.status == "ACTIVE").scalar() or 0,
            "tasks": db.query(func.count(ScrapingTask.id)).scalar() or 0,
            "organizations": db.query(func.count(Organization.id)).scalar() or 0,
            "task_leads": db.query(func.count(TaskLead.id)).scalar() or 0,
            "websites": db.query(func.count(Website.id)).scalar() or 0,
            "phones": db.query(func.count(PhoneNumber.id)).scalar() or 0,
            "emails": db.query(func.count(EmailAddress.id)).scalar() or 0,
            "social_links": db.query(func.count(SocialLink.id)).scalar() or 0
        }
    }

@router.get("/users")
def list_admin_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    user_list = []
    for u in users:
        task_count = db.query(func.count(ScrapingTask.id)).filter(ScrapingTask.user_id == u.id).scalar() or 0
        lead_count = db.query(func.count(Organization.id)).join(ScrapingTask).filter(ScrapingTask.user_id == u.id).scalar() or 0
        latest_task = db.query(ScrapingTask.created_at).filter(ScrapingTask.user_id == u.id).order_by(ScrapingTask.created_at.desc()).first()
        last_activity = latest_task[0] if latest_task else u.updated_at
        
        formatted_id = f"ADMIN-{u.id:03d}" if u.role == "ADMIN" else f"USER-{u.id:03d}"
        
        user_list.append({
            "id": u.id,
            "user_id_display": formatted_id,
            "name": u.email.split("@")[0].title(),
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at,
            "last_activity": last_activity,
            "task_count": task_count,
            "lead_count": lead_count
        })
    return user_list

@router.patch("/users/{user_id}")
def update_user_status_or_role(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    if "role" in payload and payload["role"] in ("USER", "ADMIN"):
        target_user.role = payload["role"]
    if "status" in payload and payload["status"] in ("ACTIVE", "SUSPENDED"):
        target_user.status = payload["status"]
        
    db.commit()
    db.refresh(target_user)
    return {
        "id": target_user.id,
        "email": target_user.email,
        "role": target_user.role,
        "status": target_user.status
    }

@router.get("/tasks")
def list_admin_tasks(
    user_email: Optional[str] = None,
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    query = db.query(ScrapingTask).options(joinedload(ScrapingTask.user))
    
    if user_email:
        query = query.join(User).filter(User.email.ilike(f"%{user_email}%"))
    if keyword:
        query = query.filter(ScrapingTask.keyword.ilike(f"%{keyword}%"))
    if location:
        query = query.filter(ScrapingTask.location.ilike(f"%{location}%"))
    if status:
        query = query.filter(ScrapingTask.status == status)

    tasks = query.order_by(ScrapingTask.created_at.desc()).limit(limit).all()
    if not tasks:
        return []

    task_ids = [t.id for t in tasks]
    lead_counts_query = (
        db.query(Organization.task_id, func.count(Organization.id))
        .filter(Organization.task_id.in_(task_ids))
        .group_by(Organization.task_id)
        .all()
    )
    lead_counts_map = {tid: count for tid, count in lead_counts_query if tid is not None}

    task_list = []
    for t in tasks:
        lead_count = lead_counts_map.get(t.id, 0)
        task_list.append({
            "id": t.id,
            "task_id": t.public_task_id,
            "public_task_id": t.public_task_id,
            "user_id": t.user_id,
            "user_name": t.user.email.split("@")[0].title() if t.user else "System/Guest",
            "user_email": t.user.email if t.user else "System/Guest",
            "keyword": t.keyword,
            "location": t.location,
            "status": t.status,
            "progress": t.progress,
            "discovered": t.discovered_count,
            "discovered_count": t.discovered_count,
            "websites_found": t.websites_found,
            "websites_crawled": t.websites_crawled,
            "leads_created": lead_count,
            "lead_count": lead_count,
            "created_at": t.created_at,
            "completed_at": t.completed_at
        })
    return task_list

@router.get("/logs", response_model=List[ScrapingLogResponse])
def get_admin_logs(
    task_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    query = db.query(ScrapingLog)
    if task_id:
        if task_id.isdigit():
            query = query.filter(ScrapingLog.task_id == int(task_id))
        else:
            task = db.query(ScrapingTask).filter(ScrapingTask.public_task_id == task_id).first()
            if task:
                query = query.filter(ScrapingLog.task_id == task.id)
    if event_type:
        query = query.filter(ScrapingLog.event_type == event_type)
        
    return query.order_by(ScrapingLog.created_at.desc()).limit(limit).all()

@router.get("/health")
def get_system_health(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    # Check DB
    db_status = "HEALTHY"
    try:
        db.execute(func.now())
    except Exception:
        db_status = "UNHEALTHY"

    # Find last successful and failed crawls
    last_success = db.query(ScrapingLog).filter(ScrapingLog.event_type == "CRAWL_SUCCESS").order_by(ScrapingLog.created_at.desc()).first()
    last_failure = db.query(ScrapingLog).filter(ScrapingLog.event_type.in_(["CRAWL_FAILED", "WEBSITE_FAILED", "TASK_FAILED"])).order_by(ScrapingLog.created_at.desc()).first()

    return {
        "status": "OPERATIONAL" if db_status == "HEALTHY" else "DEGRADED",
        "services": {
            "database": {"status": db_status},
            "api": {"status": "HEALTHY"},
            "crawler": {"status": "HEALTHY"},
            "playwright_fallback": {"status": "READY"},
            "discovery_provider": {"status": "HEALTHY"}
        },
        "last_successful_crawl": last_success.created_at if last_success else None,
        "last_failed_crawl": last_failure.created_at if last_failure else None
    }

# ==============================================================================
# MASTER ORGANIZATIONS ADMIN MANAGEMENT ENDPOINTS
# ==============================================================================

from app.services.location_service import normalize_target_location
from app.services.scraper.identification import normalize_category_and_subcategory
from app.models.models import OrgBranch

def validate_location_combination(state: str, district: str) -> None:
    if not state or not district:
        return
    norm = normalize_target_location(district)
    target_state = norm.get("target_state_or_ut")
    if target_state and target_state.lower() != state.lower():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Location Combination: District '{district}' belongs to '{target_state}', not '{state}'."
        )

@router.get("/organizations")
def list_admin_organizations(
    search: Optional[str] = None,
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    verification_status: Optional[str] = Query("ALL", description="ALL, ADMIN_VERIFIED, WEB_VERIFIED, UNVERIFIED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    query = db.query(Organization).options(
        joinedload(Organization.website),
        joinedload(Organization.phone_numbers),
        joinedload(Organization.email_addresses),
        joinedload(Organization.social_links),
        joinedload(Organization.branches)
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Organization.name.ilike(term),
                Organization.display_name.ilike(term),
                Organization.city.ilike(term),
                Organization.official_website_url.ilike(term)
            )
        )

    if category and category.strip():
        norm_cat, _ = normalize_category_and_subcategory(category)
        query = query.filter(Organization.category == norm_cat)

    if sub_category and sub_category.strip():
        query = query.filter(Organization.sub_category == sub_category.strip())

    if district and district.strip():
        query = query.filter(Organization.district.ilike(f"%{district.strip()}%"))

    if state and state.strip():
        query = query.filter(Organization.state.ilike(f"%{state.strip()}%"))

    if verification_status == "ADMIN_VERIFIED":
        query = query.filter(Organization.admin_verified == True)
    elif verification_status == "WEB_VERIFIED":
        query = query.filter(
            Organization.admin_verified == False,
            Organization.identity_verified == True,
            Organization.official_website_verified == True
        )
    elif verification_status == "UNVERIFIED":
        query = query.filter(
            Organization.admin_verified == False,
            or_(Organization.identity_verified == False, Organization.official_website_verified == False)
        )

    total_records = query.count()
    total_pages = (total_records + page_size - 1) // page_size

    organizations = query.order_by(Organization.updated_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    items = []
    for org in organizations:
        items.append({
            "id": org.id,
            "name": org.name,
            "display_name": org.display_name,
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
            "verification_badge": "ADMIN VERIFIED" if org.admin_verified else ("WEB VERIFIED" if org.official_website_verified else "UNVERIFIED"),
            "admin_verified": org.admin_verified,
            "verified_by": org.verified_by,
            "verified_at": org.verified_at.isoformat() if org.verified_at else None,
            "identity_verified": org.identity_verified,
            "official_website_verified": org.official_website_verified,
            "branch_count": len(org.branches) if org.branches else 0,
            "phone_count": len(org.phone_numbers) if org.phone_numbers else 0,
            "email_count": len(org.email_addresses) if org.email_addresses else 0,
            "created_at": org.created_at,
            "updated_at": org.updated_at
        })

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "items": items
    }

@router.get("/organizations/{org_id}")
def get_admin_organization_detail(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).options(
        joinedload(Organization.website),
        joinedload(Organization.phone_numbers),
        joinedload(Organization.email_addresses),
        joinedload(Organization.social_links),
        joinedload(Organization.branches)
    ).filter(Organization.id == org_id).first()

    if not org:
        raise HTTPException(status_code=404, detail=f"Organization with ID {org_id} not found.")

    return {
        "id": org.id,
        "name": org.name,
        "display_name": org.display_name,
        "category": org.category,
        "sub_category": org.sub_category,
        "description": org.description,
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
        "verification_badge": "ADMIN VERIFIED" if org.admin_verified else ("WEB VERIFIED" if org.official_website_verified else "UNVERIFIED"),
        "admin_verified": org.admin_verified,
        "verification_method": org.verification_method or ("ADMIN" if org.admin_verified else "SCRAPER_AUTOMATIC"),
        "verified_by": org.verified_by,
        "verified_at": org.verified_at,
        "identity_verified": org.identity_verified,
        "category_verified": org.category_verified,
        "country_verified": org.country_verified,
        "state_verified": org.state_verified,
        "district_verified": org.district_verified,
        "location_verified": org.location_verified,
        "official_website_verified": org.official_website_verified,
        "website": {"url": org.website.url, "domain": org.website.domain} if org.website else None,
        "phone_numbers": [{"id": p.id, "raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type} for p in org.phone_numbers],
        "email_addresses": [{"id": e.id, "email": e.email, "extraction_method": e.extraction_method} for e in org.email_addresses],
        "social_links": {
            "facebook_url": org.facebook_url,
            "instagram_url": org.instagram_url,
            "linkedin_url": org.linkedin_url,
            "youtube_url": org.youtube_url,
            "x_url": org.x_url,
            "whatsapp_url": org.whatsapp_url
        },
        "other_links": org.other_links or [],
        "branches": [
            {
                "id": b.id,
                "branch_name": b.branch_name,
                "address": b.address,
                "city": b.city,
                "district": b.district,
                "state": b.state,
                "country": b.country,
                "pincode": b.pincode,
                "phone_numbers": b.phone_numbers or [],
                "email_addresses": b.email_addresses or [],
                "website_url": b.website_url,
                "maps_url": b.maps_url
            } for b in org.branches
        ],
        "created_at": org.created_at,
        "updated_at": org.updated_at
    }

@router.post("/organizations", status_code=201)
def admin_create_organization(
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    name = (payload.get("name") or "").strip()
    raw_category = (payload.get("category") or "").strip()
    raw_sub_category = (payload.get("sub_category") or "").strip()
    district_name = (payload.get("district") or "").strip()
    state_name = (payload.get("state") or "Tamil Nadu").strip()

    if not name or not raw_category or not district_name:
        raise HTTPException(status_code=400, detail="Organization Name, Category, and District are required.")

    # Location Combination Validation
    validate_location_combination(state_name, district_name)

    # Normalize category
    norm_cat, norm_subcat = normalize_category_and_subcategory(raw_category)
    final_subcat = raw_sub_category or norm_subcat

    # District lookup
    district_obj = db.query(District).filter(District.district_name.ilike(f"%{district_name}%")).first()
    dist_id = district_obj.id if district_obj else None

    # Duplicate check
    existing = db.query(Organization).filter(Organization.name.ilike(name), Organization.district.ilike(district_name)).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Organization '{existing.name}' in district '{district_name}' already exists (ID: {existing.id})."
        )

    system_task = db.query(ScrapingTask).filter(ScrapingTask.public_task_id == "SYSTEM-MANUAL").first()
    if not system_task:
        system_task = ScrapingTask(
            user_id=admin_user.id,
            public_task_id="SYSTEM-MANUAL",
            location="System",
            keyword="Manual Entry",
            status="COMPLETED"
        )
        db.add(system_task)
        db.commit()
        db.refresh(system_task)

    web_url = (payload.get("official_website_url") or payload.get("website") or "").strip()
    if web_url:
        from urllib.parse import urlparse
        parsed = urlparse(web_url)
        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172.16."):
            raise HTTPException(status_code=400, detail="Invalid website URL: SSRF protection blocked access to internal/private network addresses.")

    org = Organization(
        task_id=system_task.id,
        district_id=dist_id,
        name=name,
        display_name=payload.get("display_name") or None,
        category=norm_cat,
        sub_category=final_subcat,
        description=payload.get("description") or None,
        district=district_name,
        state=state_name,
        city=payload.get("city") or district_name,
        address=payload.get("address") or None,
        country=payload.get("country") or "India",
        pincode=payload.get("pincode") or None,
        official_website_url=web_url or None,
        google_maps_url=payload.get("google_maps_url") or None,
        facebook_url=payload.get("facebook_url") or None,
        instagram_url=payload.get("instagram_url") or None,
        linkedin_url=payload.get("linkedin_url") or None,
        youtube_url=payload.get("youtube_url") or None,
        x_url=payload.get("x_url") or None,
        whatsapp_url=payload.get("whatsapp_url") or None,
        other_links=payload.get("other_links") or [],
        admin_verified=True,
        source_type="ADMIN_VERIFIED",
        verification_method="ADMIN",
        verified_by=admin_user.email,
        verified_at=datetime.datetime.utcnow(),
        confidence="HIGH",
        is_quarantined=bool(payload.get("is_quarantined", False)),
        quarantine_reason=payload.get("quarantine_reason") or None
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Optional website model entry
    if web_url:
        domain_part = web_url.replace("https://", "").replace("http://", "").split("/")[0]
        web = db.query(Website).filter(Website.organization_id == org.id).first()
        if web:
            web.url = web_url
            web.domain = domain_part
            web.status = "ACTIVE"
        else:
            web = Website(
                organization_id=org.id,
                url=web_url,
                domain=domain_part,
                status="ACTIVE",
                discovery_source="ADMIN_MANUAL",
                confidence="HIGH"
            )
            db.add(web)

    # Process Phones List
    phones_list = payload.get("phone_numbers") or []
    if not phones_list and payload.get("phone"):
        phones_list = [{"raw_value": payload["phone"], "normalized_value": payload["phone"], "type": "office"}]

    for p in phones_list:
        raw_val = (p.get("raw_value") or p.get("phone") or "").strip()
        norm_val = (p.get("normalized_value") or raw_val).strip()
        if raw_val:
            pn = PhoneNumber(
                organization_id=org.id,
                raw_value=raw_val,
                normalized_value=norm_val,
                type=p.get("type") or "office"
            )
            db.add(pn)

    # Process Emails List
    emails_list = payload.get("email_addresses") or []
    if not emails_list and payload.get("email"):
        emails_list = [{"email": payload["email"], "extraction_method": "admin_manual"}]

    for e in emails_list:
        em_val = (e.get("email") if isinstance(e, dict) else e or "").strip()
        if em_val:
            em = EmailAddress(
                organization_id=org.id,
                email=em_val,
                extraction_method=(e.get("extraction_method") if isinstance(e, dict) else "admin_manual")
            )
            db.add(em)

    # Process Branches List
    branches_list = payload.get("branches") or []
    for b in branches_list:
        b_name = (b.get("branch_name") or "").strip()
        b_dist = (b.get("district") or district_name).strip()
        b_state = (b.get("state") or state_name).strip()
        if b_name:
            validate_location_combination(b_state, b_dist)
            branch_obj = OrgBranch(
                organization_id=org.id,
                branch_name=b_name,
                address=b.get("address"),
                city=b.get("city") or b_dist,
                district=b_dist,
                state=b_state,
                country=b.get("country") or "India",
                pincode=b.get("pincode"),
                phone_numbers=b.get("phone_numbers") or [],
                email_addresses=b.get("email_addresses") or [],
                website_url=b.get("website_url"),
                maps_url=b.get("maps_url")
            )
            db.add(branch_obj)

    db.commit()
    db.refresh(org)

    print(f"[ADMIN ORG CREATED] Org ID {org.id} '{org.name}' ({org.district}, {org.state}) - Admin Verified")

    return get_admin_organization_detail(org.id, db, admin_user)

@router.put("/organizations/{org_id}")
def admin_update_organization(
    org_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization with ID {org_id} not found.")

    district_name = (payload.get("district") or org.district or "").strip()
    state_name = (payload.get("state") or org.state or "Tamil Nadu").strip()

    validate_location_combination(state_name, district_name)

    if "name" in payload and payload["name"].strip():
        org.name = payload["name"].strip()
    if "display_name" in payload:
        org.display_name = payload["display_name"] or None
    if "category" in payload and payload["category"].strip():
        norm_cat, norm_subcat = normalize_category_and_subcategory(payload["category"])
        org.category = norm_cat
        if not payload.get("sub_category"):
            org.sub_category = norm_subcat
    if "sub_category" in payload and payload["sub_category"]:
        org.sub_category = payload["sub_category"]
    if "description" in payload:
        org.description = payload["description"]
    if "district" in payload:
        org.district = district_name
    if "state" in payload:
        org.state = state_name
    if "city" in payload:
        org.city = payload["city"]
    if "address" in payload:
        org.address = payload["address"]
    if "pincode" in payload:
        org.pincode = payload["pincode"]
    if "official_website_url" in payload or "website" in payload:
        web_url = payload.get("official_website_url") or payload.get("website") or ""
        org.official_website_url = web_url or None

    if "google_maps_url" in payload: org.google_maps_url = payload["google_maps_url"]
    if "facebook_url" in payload: org.facebook_url = payload["facebook_url"]
    if "instagram_url" in payload: org.instagram_url = payload["instagram_url"]
    if "linkedin_url" in payload: org.linkedin_url = payload["linkedin_url"]
    if "youtube_url" in payload: org.youtube_url = payload["youtube_url"]
    if "x_url" in payload: org.x_url = payload["x_url"]
    if "whatsapp_url" in payload: org.whatsapp_url = payload["whatsapp_url"]
    if "other_links" in payload: org.other_links = payload["other_links"]
    if "is_quarantined" in payload: org.is_quarantined = bool(payload["is_quarantined"])
    if "quarantine_reason" in payload: org.quarantine_reason = payload["quarantine_reason"]

    # Explicitly set Admin Verified
    org.admin_verified = True
    org.source_type = "ADMIN_VERIFIED"
    org.verification_method = "ADMIN"
    org.verified_by = admin_user.email
    org.verified_at = datetime.datetime.utcnow()
    org.updated_at = datetime.datetime.utcnow()

    # Update Phones if provided
    if "phone_numbers" in payload and isinstance(payload["phone_numbers"], list):
        db.query(PhoneNumber).filter(PhoneNumber.organization_id == org.id).delete()
        for p in payload["phone_numbers"]:
            raw_v = (p.get("raw_value") or "").strip()
            norm_v = (p.get("normalized_value") or raw_v).strip()
            if raw_v:
                db.add(PhoneNumber(organization_id=org.id, raw_value=raw_v, normalized_value=norm_v, type=p.get("type") or "office"))

    # Update Emails if provided
    if "email_addresses" in payload and isinstance(payload["email_addresses"], list):
        db.query(EmailAddress).filter(EmailAddress.organization_id == org.id).delete()
        for e in payload["email_addresses"]:
            em_val = (e.get("email") if isinstance(e, dict) else e or "").strip()
            if em_val:
                db.add(EmailAddress(
                    organization_id=org.id,
                    email=em_val,
                    extraction_method=(e.get("extraction_method") if isinstance(e, dict) else "admin_manual")
                ))

    # Update Branches if provided
    if "branches" in payload and isinstance(payload["branches"], list):
        db.query(OrgBranch).filter(OrgBranch.organization_id == org.id).delete()
        for b in payload["branches"]:
            b_name = (b.get("branch_name") or "").strip()
            b_dist = (b.get("district") or district_name).strip()
            b_state = (b.get("state") or state_name).strip()
            if b_name:
                validate_location_combination(b_state, b_dist)
                db.add(OrgBranch(
                    organization_id=org.id,
                    branch_name=b_name,
                    address=b.get("address"),
                    city=b.get("city") or b_dist,
                    district=b_dist,
                    state=b_state,
                    country=b.get("country") or "India",
                    pincode=b.get("pincode"),
                    phone_numbers=b.get("phone_numbers") or [],
                    email_addresses=b.get("email_addresses") or [],
                    website_url=b.get("website_url"),
                    maps_url=b.get("maps_url")
                ))

    db.commit()
    db.refresh(org)

    print(f"[ADMIN ORG UPDATED] Org ID {org.id} '{org.name}' updated by Admin.")

    return get_admin_organization_detail(org.id, db, admin_user)

@router.delete("/organizations/{org_id}")
def admin_delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    
    org_name = org.name
    # Explicitly remove child relationships
    db.query(Website).filter(Website.organization_id == org_id).delete(synchronize_session=False)
    db.query(PhoneNumber).filter(PhoneNumber.organization_id == org_id).delete(synchronize_session=False)
    db.query(EmailAddress).filter(EmailAddress.organization_id == org_id).delete(synchronize_session=False)
    db.query(SocialLink).filter(SocialLink.organization_id == org_id).delete(synchronize_session=False)
    db.query(OrgBranch).filter(OrgBranch.organization_id == org_id).delete(synchronize_session=False)
    db.query(TaskLead).filter(TaskLead.organization_id == org_id).delete(synchronize_session=False)
    db.delete(org)
    db.commit()
    return {"message": f"Organization '{org_name}' (ID: {org_id}) deleted successfully."}

@router.post("/organizations/{org_id}/branches", status_code=201)
def admin_add_branch(
    org_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization ID {org_id} not found.")

    b_name = (payload.get("branch_name") or "").strip()
    b_dist = (payload.get("district") or org.district or "").strip()
    b_state = (payload.get("state") or org.state or "Tamil Nadu").strip()

    if not b_name or not b_dist:
        raise HTTPException(status_code=400, detail="Branch Name and District are required.")

    validate_location_combination(b_state, b_dist)

    branch = OrgBranch(
        organization_id=org.id,
        branch_name=b_name,
        address=payload.get("address"),
        city=payload.get("city") or b_dist,
        district=b_dist,
        state=b_state,
        country=payload.get("country") or "India",
        pincode=payload.get("pincode"),
        phone_numbers=payload.get("phone_numbers") or [],
        email_addresses=payload.get("email_addresses") or [],
        website_url=payload.get("website_url"),
        maps_url=payload.get("maps_url")
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    return {
        "id": branch.id,
        "organization_id": org.id,
        "branch_name": branch.branch_name,
        "district": branch.district,
        "state": branch.state,
        "message": f"Branch '{branch.branch_name}' added to Organization '{org.name}'."
    }

@router.delete("/branches/{branch_id}")
def admin_delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    branch = db.query(OrgBranch).filter(OrgBranch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail=f"Branch ID {branch_id} not found.")

    b_name = branch.branch_name
    db.delete(branch)
    db.commit()
    return {"message": f"Branch '{b_name}' (ID: {branch_id}) deleted successfully."}

@router.post("/organizations/{org_id}/verify")
def admin_verify_organization(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization ID {org_id} not found.")

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
        "message": f"Organization '{org.name}' verified successfully by Admin.",
        "id": org.id,
        "admin_verified": True,
        "source_type": org.source_type
    }

@router.post("/organizations/{org_id}/unverify")
def admin_unverify_organization(
    org_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization ID {org_id} not found.")

    if org.admin_verified:
        org.admin_verified = False
        org.source_type = org.previous_source_type or ("MANUAL" if org.verification_method == "ADMIN" else "SCRAPER_VERIFIED")
        org.verified_by = None
        org.verified_at = None
        org.updated_at = datetime.datetime.utcnow()
        db.commit()

    return {
        "message": f"Organization '{org.name}' unverified successfully by Admin.",
        "id": org.id,
        "admin_verified": False,
        "source_type": org.source_type
    }
