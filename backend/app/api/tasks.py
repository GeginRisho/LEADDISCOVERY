from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import io
from app.core.database import get_db
from app.models.models import ScrapingTask, Organization, ScrapingLog
from app.schemas.tasks import ScrapingTaskCreate, ScrapingTaskResponse, ScrapingLogResponse
from app.schemas.leads import OrganizationLeadResponse
from app.api.auth import get_current_user
from app.services.scraper.worker import run_scraping_task, log_event, sync_task_counters
from app.services.exporter import export_leads_to_csv, export_leads_to_excel

router = APIRouter(prefix="/tasks", tags=["Scraping Tasks"])

def find_task_by_id_or_public(task_id: str, db: Session) -> ScrapingTask:
    # Support looking up either by public_task_id (e.g. TASK-000001) or by integer ID
    task = db.query(ScrapingTask).filter(ScrapingTask.public_task_id == task_id).first()
    if not task and task_id.isdigit():
        task = db.query(ScrapingTask).filter(ScrapingTask.id == int(task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Scraping task '{task_id}' not found.")
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

    # 1. Create task in DB with authenticated user's ID
    task = ScrapingTask(
        user_id=current_user.id,
        public_task_id="TEMP",
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
    from app.services.location_service import normalize_target_location
    from app.services.scraper.identification import normalize_category_and_subcategory
    from app.models.models import TaskLead

    norm_cat, norm_subcat = normalize_category_and_subcategory(payload.keyword)
    target_loc = normalize_target_location(payload.location)
    target_min = min(15, payload.max_results) if payload.max_results >= 15 else payload.max_results

    query = db.query(Organization).filter(
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

    if norm_subcat and norm_subcat != norm_cat:
        query = query.filter(Organization.sub_category == norm_subcat)

    if target_loc["target_district"]:
        query = query.filter(Organization.district == target_loc["target_district"])
    if target_loc["target_state_or_ut"]:
        query = query.filter(Organization.state == target_loc["target_state_or_ut"])

    pre_verified_orgs = query.limit(target_min).all()

    # Create immediate TaskLead links
    for org in pre_verified_orgs:
        tl = TaskLead(
            task_id=task.id,
            organization_id=org.id,
            qualification_status="QUALIFIED",
            confidence=org.confidence,
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
    
    return task

@router.get("", response_model=List[ScrapingTaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user and current_user.role == "ADMIN":
        tasks = db.query(ScrapingTask).order_by(ScrapingTask.created_at.desc()).all()
    elif current_user:
        tasks = db.query(ScrapingTask).filter(ScrapingTask.user_id == current_user.id).order_by(ScrapingTask.created_at.desc()).all()
    else:
        tasks = []

    for t in tasks:
        if t.status in ("COMPLETED", "COMPLETED_BELOW_MINIMUM", "FAILED", "COMPLETED_WITH_NO_RESULTS"):
            sync_task_counters(db, t.id)
    return tasks

@router.get("/{task_id}", response_model=ScrapingTaskResponse)
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    task = find_task_by_id_or_public(task_id, db)
    if current_user.role != "ADMIN" and task.user_id and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this task.")
    
    if task.status in ("COMPLETED", "COMPLETED_BELOW_MINIMUM", "FAILED", "COMPLETED_WITH_NO_RESULTS"):
        sync_task_counters(db, task.id)
        db.refresh(task)
        
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
            ).all()
    else:
        leads = db.query(Organization).filter(Organization.task_id == task.id)\
            .options(
                joinedload(Organization.website),
                joinedload(Organization.phone_numbers),
                joinedload(Organization.email_addresses),
                joinedload(Organization.social_links)
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
