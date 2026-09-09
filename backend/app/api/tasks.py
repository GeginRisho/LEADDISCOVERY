from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import or_, and_, func, case
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import io
import datetime
from app.core.database import get_db
from app.models.models import ScrapingTask, Organization, ScrapingLog, TaskLead, User
from app.schemas.tasks import ScrapingTaskCreate, ScrapingTaskResponse, ScrapingLogResponse
from app.schemas.leads import OrganizationLeadResponse
from app.api.auth import get_current_user
from app.services.scraper.worker import run_scraping_task, log_event, sync_task_counters
from app.services.exporter import export_leads_to_csv, export_leads_to_excel

router = APIRouter(prefix="/tasks", tags=["Scraping Tasks"])

def find_task_by_id_or_public(task_id: str, db: Session) -> ScrapingTask:
    # Support looking up either by public_task_id (e.g. TASK-000001) or by integer ID
    task = db.query(ScrapingTask).options(joinedload(ScrapingTask.user)).filter(ScrapingTask.public_task_id == task_id).first()
    if not task and task_id.isdigit():
        task = db.query(ScrapingTask).options(joinedload(ScrapingTask.user)).filter(ScrapingTask.id == int(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Scraping task '{task_id}' not found.")
    count = db.query(func.count(TaskLead.id)).filter(TaskLead.task_id == task.id).scalar() or 0
    if count == 0:
        count = db.query(func.count(Organization.id)).filter(Organization.task_id == task.id).scalar() or 0
    task._lead_count = count
    task._user_email = task.user.email if task.user else "System/Guest"
    task._social_count = 0
    return task

def is_lead_qualified(lead: Organization, required_fields: Optional[List[str]]) -> bool:
    if not lead.name or not lead.name.strip():
        return False

    if required_fields:
        req_lower = [f.lower().strip() for f in required_fields]

        for req in req_lower:
            if req in ("phone", "phones", "phone_number"):
                if not lead.phone_numbers or len(lead.phone_numbers) == 0:
                    return False
            elif req in ("email", "emails", "email_address"):
                if not lead.email_addresses or len(lead.email_addresses) == 0:
                    return False
            elif req in ("website", "url", "domain"):
                if not lead.website or not (lead.website.url or lead.website.domain):
                    return False
            elif req in ("address", "location"):
                if not lead.address or len(lead.address.strip()) == 0:
                    return False

    # Default minimum qualification: Real organization identity verified + official website OR discovery source OR contact/address detail
    has_website = bool(lead.website and (lead.website.url or lead.website.domain))
    has_discovery_source = bool(lead.discovery_source_url and len(lead.discovery_source_url.strip()) > 0)
    has_phone = bool(lead.phone_numbers and len(lead.phone_numbers) > 0)
    has_email = bool(lead.email_addresses and len(lead.email_addresses) > 0)
    has_address = bool(lead.address and len(lead.address.strip()) > 0)

    if not (has_website or has_discovery_source or has_phone or has_email or has_address):
        return False

    return True


def get_initial_verified_organizations(
    db: Session,
    keyword: str,
    location: str,
    limit: int = 15
) -> List[Organization]:
    from app.services.location_service import normalize_target_location
    from app.services.scraper.identification import normalize_category_and_subcategory
    from sqlalchemy import func, or_, and_
    from sqlalchemy.orm import joinedload

    if not keyword or not location:
        return []

    kw_clean = keyword.strip().lower()
    norm_cat, norm_subcat = normalize_category_and_subcategory(keyword)
    target_loc = normalize_target_location(location)

    # 1. CATEGORY MATCHING (Synonyms, Plurals & Subcategories)
    cat_terms = set()
    kw_words = [w.strip() for w in kw_clean.replace("&", " ").split() if len(w.strip()) > 2]
    for w in kw_words:
        if w.endswith("s") and len(w) > 3:
            cat_terms.add(w[:-1])
        cat_terms.add(w)

    cat_terms.add(kw_clean)
    if norm_cat:
        cat_terms.add(norm_cat.lower())
        if norm_cat.lower().endswith("s") and len(norm_cat) > 3:
            cat_terms.add(norm_cat.lower()[:-1])
    if norm_subcat:
        cat_terms.add(norm_subcat.lower())

    if "hotel" in kw_clean:
        cat_terms.update(["hotel", "resort", "lodging", "accommodation", "hospitality"])
    elif "school" in kw_clean:
        cat_terms.update(["school", "cbse", "matriculation", "academy"])
    elif "college" in kw_clean:
        cat_terms.update(["college", "university", "institution"])
    elif "hospital" in kw_clean:
        cat_terms.update(["hospital", "clinic", "medical", "healthcare"])
    elif "company" in kw_clean or "software" in kw_clean or "it" in kw_clean:
        cat_terms.update(["company", "software", "tech", "it"])

    cat_clauses = []
    for term in cat_terms:
        if not term:
            continue
        cat_clauses.append(func.lower(Organization.category) == term)
        cat_clauses.append(func.lower(Organization.category).like(f"%{term}%"))
        cat_clauses.append(func.lower(Organization.sub_category) == term)
        cat_clauses.append(func.lower(Organization.sub_category).like(f"%{term}%"))

    # 2. LOCATION MATCHING (Strict District & Regional Protection)
    target_dist = target_loc.get("target_district", "").lower()
    target_state = target_loc.get("target_state_or_ut", "").lower()
    valid_cities = [c.lower() for c in target_loc.get("valid_cities_in_district", set())]

    dist_synonyms = [target_dist] if target_dist else []
    if target_dist in ("puducherry", "pondicherry") or target_state in ("puducherry ut", "puducherry"):
        dist_synonyms = ["puducherry", "pondicherry", "puducherry ut"]

    city_list = list(set(valid_cities + dist_synonyms))

    loc_clauses = []
    if target_loc.get("target_country"):
        loc_clauses.append(func.lower(Organization.country) == target_loc["target_country"].lower())

    if city_list:
        sub_locs = [
            func.lower(Organization.district).in_(dist_synonyms),
            func.lower(Organization.city).in_(city_list),
            func.lower(Organization.state).in_(dist_synonyms)
        ]
        for c in dist_synonyms:
            if len(c) >= 4:
                sub_locs.append(func.lower(Organization.address).like(f"%{c}%"))
        loc_clauses.append(or_(*sub_locs))
    elif target_state:
        loc_clauses.append(or_(
            func.lower(Organization.state) == target_state,
            func.lower(Organization.district) == target_state
        ))

    # 3. VERIFIED ELIGIBILITY & NOT QUARANTINED
    scraper_verified_clause = and_(
        Organization.identity_verified == True,
        Organization.category_verified == True,
        Organization.country_verified == True,
        Organization.state_verified == True,
        Organization.district_verified == True,
        Organization.location_verified == True,
        Organization.official_website_verified == True
    )

    verified_clause = or_(
        Organization.admin_verified == True,
        Organization.source_type == "ADMIN_VERIFIED",
        Organization.verification_method == "ADMIN",
        scraper_verified_clause,
        and_(
            Organization.confidence.in_(["HIGH", "MEDIUM"]),
            Organization.official_website_verified == True
        )
    )

    not_quarantined_clause = or_(
        Organization.is_quarantined == False,
        Organization.is_quarantined.is_(None)
    )

    query = db.query(Organization).filter(
        or_(*cat_clauses),
        and_(*loc_clauses),
        verified_clause,
        not_quarantined_clause
    ).options(
        joinedload(Organization.website),
        joinedload(Organization.phone_numbers),
        joinedload(Organization.email_addresses),
        joinedload(Organization.social_links)
    ).order_by(
        Organization.admin_verified.desc(),
        Organization.confidence.desc(),
        Organization.id.desc()
    ).limit(limit)

    return query.all()

@router.post("", response_model=ScrapingTaskResponse, status_code=status.HTTP_201_CREATED)
@router.post("/scrape", response_model=ScrapingTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: ScrapingTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    import time
    t_start = time.time()

    # 0. Idempotency check: if client_request_id provided, return existing task if created recently
    clean_req_id = payload.client_request_id.strip() if payload.client_request_id and payload.client_request_id.strip() else None
    if clean_req_id:
        fifteen_mins_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        existing = db.query(ScrapingTask).filter(
            ScrapingTask.client_request_id == clean_req_id,
            ScrapingTask.user_id == current_user.id,
            ScrapingTask.created_at >= fifteen_mins_ago
        ).first()
        if existing:
            return existing

    # 1. Create task in DB with authenticated user's ID
    task = ScrapingTask(
        user_id=current_user.id,
        public_task_id="TEMP",
        client_request_id=clean_req_id,
        location=payload.location,
        keyword=payload.keyword,
        radius=payload.radius,
        max_results=payload.max_results,
        max_pages_per_site=payload.max_pages_per_site,
        requested_fields=payload.requested_fields,
        required_fields=payload.required_fields,
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 2. Formatted public task ID
    task.public_task_id = f"TASK-{task.id:06d}"
    db.commit()
    db.refresh(task)
    
    log_event(db, task.id, "TASK_CREATED", f"Scraping task initialized with ID: {task.public_task_id} by user: {current_user.email}")

    # 3. FAST READ PATH: Query Master Organizations verified index immediately
    from app.models.models import TaskLead

    target_min = min(15, payload.max_results) if payload.max_results >= 15 else payload.max_results
    pre_verified_orgs = get_initial_verified_organizations(db, payload.keyword, payload.location, limit=target_min)

    # Create immediate TaskLead links safely
    existing_lead_org_ids = {tl.organization_id for tl in db.query(TaskLead.organization_id).filter(TaskLead.task_id == task.id).all()}
    added_org_ids = set()

    for org in pre_verified_orgs:
        if org.id not in existing_lead_org_ids and org.id not in added_org_ids:
            added_org_ids.add(org.id)
            tl = TaskLead(
                task_id=task.id,
                organization_id=org.id,
                qualification_status="QUALIFIED",
                confidence=org.confidence or "HIGH",
                identity_verified=True,
                category_verified=True,
                location_verified=True,
                official_website_verified=True
            )
            db.add(tl)

    db.commit()
    sync_task_counters(db, task.id)
    db.refresh(task)

    fast_count = len(pre_verified_orgs)
    dur_ms = round((time.time() - t_start) * 1000, 2)

    log_event(
        db, task.id, "FAST_READ_PATH",
        f"[FAST READ PATH] Returned {fast_count} pre-verified master organizations in {dur_ms}ms (Target: {target_min})."
    )

    # 4. Check if target minimum is satisfied by Fast Index
    if fast_count >= target_min:
        task.status = "COMPLETED"
        task.progress = 100
        task.completed_at = datetime.datetime.utcnow()
        db.commit()
        log_event(db, task.id, "TASK_COMPLETED", f"[FAST SEARCH COMPLETED] Target {target_min} satisfied by Fast Verified Index.")
    else:
        # Dispatch background discovery ONLY for missing target slots
        task.status = "RUNNING"
        task.progress = min(10 + int((fast_count / target_min) * 50), 60) if target_min > 0 else 10
        db.commit()
        background_tasks.add_task(run_scraping_task, task.id)
    
    task.fast_verified_results = pre_verified_orgs
    return task

@router.get("", response_model=List[ScrapingTaskResponse])
@router.get("/history", response_model=List[ScrapingTaskResponse])
def list_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    offset = (page - 1) * limit
    query = db.query(ScrapingTask).options(joinedload(ScrapingTask.user))
    if current_user and current_user.role == "ADMIN":
        pass
    elif current_user:
        query = query.filter(ScrapingTask.user_id == current_user.id)
    else:
        return []

    tasks = query.order_by(ScrapingTask.created_at.desc()).offset(offset).limit(limit).all()
    if not tasks:
        return []

    task_ids = [t.id for t in tasks]

    # Efficient aggregated lead count query without loading orgs or leads
    lead_counts_query = (
        db.query(TaskLead.task_id, func.count(TaskLead.id))
        .filter(TaskLead.task_id.in_(task_ids))
        .group_by(TaskLead.task_id)
        .all()
    )
    lead_counts_map = {tid: count for tid, count in lead_counts_query if tid is not None}

    # Also count from Organization.task_id for legacy manual/scraper tasks
    org_counts_query = (
        db.query(Organization.task_id, func.count(Organization.id))
        .filter(Organization.task_id.in_(task_ids))
        .group_by(Organization.task_id)
        .all()
    )
    org_counts_map = {tid: count for tid, count in org_counts_query if tid is not None}

    for t in tasks:
        leads_total = lead_counts_map.get(t.id, 0)
        if leads_total == 0:
            leads_total = org_counts_map.get(t.id, 0)
        t._lead_count = leads_total
        t._social_count = 0
        t._user_email = t.user.email if t.user else "System/Guest"

    return tasks

@router.get("/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    base_query = db.query(
        func.count(ScrapingTask.id).label("total_tasks"),
        func.coalesce(func.sum(ScrapingTask.websites_found), 0).label("total_websites_found"),
        func.coalesce(func.sum(ScrapingTask.websites_crawled), 0).label("total_crawled"),
        func.coalesce(func.sum(ScrapingTask.failed_count), 0).label("total_failed"),
        func.sum(case((ScrapingTask.status == "RUNNING", 1), else_=0)).label("running_tasks"),
        func.sum(case((ScrapingTask.status == "COMPLETED", 1), else_=0)).label("completed_tasks")
    )
    if current_user.role != "ADMIN":
        base_query = base_query.filter(ScrapingTask.user_id == current_user.id)
    
    stats_row = base_query.first()

    recent_query = db.query(ScrapingTask)
    if current_user.role != "ADMIN":
        recent_query = recent_query.filter(ScrapingTask.user_id == current_user.id)
    recent_tasks = recent_query.order_by(ScrapingTask.created_at.desc()).limit(5).all()

    return {
        "stats": {
            "total_tasks": int(stats_row.total_tasks or 0),
            "total_websites_found": int(stats_row.total_websites_found or 0),
            "total_crawled": int(stats_row.total_crawled or 0),
            "total_failed": int(stats_row.total_failed or 0),
            "running_tasks": int(stats_row.running_tasks or 0),
            "completed_tasks": int(stats_row.completed_tasks or 0),
        },
        "recent_tasks": [
            {
                "id": t.id,
                "public_task_id": t.public_task_id,
                "keyword": t.keyword,
                "location": t.location,
                "status": t.status,
                "progress": t.progress,
                "websites_found": t.websites_found or 0,
                "websites_crawled": t.websites_crawled or 0,
                "discovered_count": t.discovered_count or 0,
                "failed_count": t.failed_count or 0,
                "created_at": t.created_at,
                "completed_at": t.completed_at
            }
            for t in recent_tasks
        ]
    }

@router.get("/{task_id}", response_model=ScrapingTaskResponse)
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    if current_user.role != "ADMIN" and task.user_id and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this task.")
    return task

@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    if current_user.role != "ADMIN" and task.user_id and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this task.")
    if task.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a task that is already '{task.status}'.")
        
    task.status = "CANCELLED"
    db.commit()
    log_event(db, task.id, "TASK_CANCELLED", "Scraping task was cancelled by user request.")
    return {"message": f"Task '{task.public_task_id}' has been cancelled."}

@router.get("/{task_id}/logs", response_model=List[ScrapingLogResponse])
def get_task_logs(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    if current_user.role != "ADMIN" and task.user_id and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this task.")
    return db.query(ScrapingLog).filter(ScrapingLog.task_id == task.id).order_by(ScrapingLog.created_at.asc()).all()

@router.get("/{task_id}/leads", response_model=List[OrganizationLeadResponse])
def get_task_leads(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    if current_user.role != "ADMIN" and task.user_id and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this task.")
    from sqlalchemy.orm import joinedload
    from app.models.models import TaskLead
    
    task_leads = db.query(TaskLead).filter(TaskLead.task_id == task.id).all()
    if task_leads:
        org_ids = [tl.organization_id for tl in task_leads]
        leads = db.query(Organization).filter(Organization.id.in_(org_ids))\
            .options(
                joinedload(Organization.website),
                joinedload(Organization.phone_numbers),
                joinedload(Organization.email_addresses),
                joinedload(Organization.social_links)
            ).order_by(
                Organization.admin_verified.desc(),
                Organization.confidence.desc(),
                Organization.updated_at.desc(),
                Organization.id.asc()
            ).all()
    else:
        leads = db.query(Organization).filter(Organization.task_id == task.id)\
            .options(
                joinedload(Organization.website),
                joinedload(Organization.phone_numbers),
                joinedload(Organization.email_addresses),
                joinedload(Organization.social_links)
            ).order_by(
                Organization.admin_verified.desc(),
                Organization.confidence.desc(),
                Organization.updated_at.desc(),
                Organization.id.asc()
            ).all()
        
    qualified_leads = [lead for lead in leads if is_lead_qualified(lead, task.required_fields)]
    return qualified_leads

@router.get("/{task_id}/export/csv")
def export_csv(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    
    # Eager load relations for export
    from sqlalchemy.orm import subqueryload
    leads = db.query(Organization).filter(Organization.task_id == task.id)\
        .options(
            subqueryload(Organization.website),
            subqueryload(Organization.phone_numbers),
            subqueryload(Organization.email_addresses),
            subqueryload(Organization.social_links)
        ).all()
        
    leads = [lead for lead in leads if is_lead_qualified(lead, task.required_fields)]
        
    # Serialize to dict list matching exporter format
    leads_dict = []
    for lead in leads:
        lead_dict = {
            "name": lead.name,
            "category": lead.category,
            "address": lead.address,
            "city": lead.city,
            "state": lead.state,
            "pincode": lead.pincode,
            "confidence": lead.confidence,
            "created_at": lead.created_at,
            "website": {"url": lead.website.url} if lead.website else None,
            "phone_numbers": [{"raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type, "source_page_url": p.source_page.url if p.source_page else None} for p in lead.phone_numbers],
            "email_addresses": [{"email": e.email, "extraction_method": e.extraction_method, "source_page_url": e.source_page.url if e.source_page else None} for e in lead.email_addresses],
            "social_links": [{"platform": s.platform, "url": s.url, "source_page_url": s.source_page.url if s.source_page else None} for s in lead.social_links],
            "people": [] # Extractor structure maps here
        }
        leads_dict.append(lead_dict)
        
    csv_data = export_leads_to_csv(leads_dict)
    
    # Stream response
    filename = f"{task.public_task_id}_leads.csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)

@router.get("/{task_id}/export/excel")
def export_excel(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    
    # Eager load relations for export
    from sqlalchemy.orm import subqueryload
    leads = db.query(Organization).filter(Organization.task_id == task.id)\
        .options(
            subqueryload(Organization.website),
            subqueryload(Organization.phone_numbers),
            subqueryload(Organization.email_addresses),
            subqueryload(Organization.social_links)
        ).all()
        
    leads = [lead for lead in leads if is_lead_qualified(lead, task.required_fields)]
        
    leads_dict = []
    for lead in leads:
        lead_dict = {
            "name": lead.name,
            "category": lead.category,
            "address": lead.address,
            "city": lead.city,
            "state": lead.state,
            "pincode": lead.pincode,
            "confidence": lead.confidence,
            "created_at": lead.created_at,
            "website": {"url": lead.website.url} if lead.website else None,
            "phone_numbers": [{"raw_value": p.raw_value, "normalized_value": p.normalized_value, "type": p.type, "source_page_url": p.source_page.url if p.source_page else None} for p in lead.phone_numbers],
            "email_addresses": [{"email": e.email, "extraction_method": e.extraction_method, "source_page_url": e.source_page.url if e.source_page else None} for e in lead.email_addresses],
            "social_links": [{"platform": s.platform, "url": s.url, "source_page_url": s.source_page.url if s.source_page else None} for s in lead.social_links],
            "people": []
        }
        leads_dict.append(lead_dict)
        
    excel_data = export_leads_to_excel(leads_dict)
    
    filename = f"{task.public_task_id}_leads.xlsx"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
