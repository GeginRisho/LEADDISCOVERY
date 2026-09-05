from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
import datetime

from app.core.database import get_db
from app.models.models import (
    User, ScrapingTask, Organization, Website, 
    PhoneNumber, EmailAddress, SocialLink, ScrapingLog, District
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
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_admins = db.query(func.count(User.id)).filter(User.role == "ADMIN").scalar() or 0
    total_normal_users = db.query(func.count(User.id)).filter(User.role == "USER").scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.status == "ACTIVE").scalar() or 0
    suspended_users = db.query(func.count(User.id)).filter(User.status == "SUSPENDED").scalar() or 0

    total_tasks = db.query(func.count(ScrapingTask.id)).scalar() or 0
    running_tasks = db.query(func.count(ScrapingTask.id)).filter(ScrapingTask.status == "RUNNING").scalar() or 0
    completed_tasks = db.query(func.count(ScrapingTask.id)).filter(ScrapingTask.status == "COMPLETED").scalar() or 0
    failed_tasks = db.query(func.count(ScrapingTask.id)).filter(ScrapingTask.status == "FAILED").scalar() or 0

    total_discovered = db.query(func.sum(ScrapingTask.discovered_count)).scalar() or 0
    total_websites_found = db.query(func.sum(ScrapingTask.websites_found)).scalar() or 0
    total_websites_crawled = db.query(func.sum(ScrapingTask.websites_crawled)).scalar() or 0
    total_failed_crawls = db.query(func.sum(ScrapingTask.failed_count)).scalar() or 0

    total_leads = db.query(func.count(Organization.id)).scalar() or 0
    total_emails = db.query(func.count(EmailAddress.id)).scalar() or 0
    total_phones = db.query(func.count(PhoneNumber.id)).scalar() or 0
    total_socials = db.query(func.count(SocialLink.id)).scalar() or 0

    return {
        "total_users": total_users,
        "total_admins": total_admins,
        "total_normal_users": total_normal_users,
        "active_users": active_users,
        "suspended_users": suspended_users,
        "total_tasks": total_tasks,
        "running_tasks": running_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "total_discovered": total_discovered,
        "total_websites_found": total_websites_found,
        "total_websites_crawled": total_websites_crawled,
        "total_failed_crawls": total_failed_crawls,
        "total_leads": total_leads,
        "total_emails": total_emails,
        "total_phones": total_phones,
        "total_socials": total_socials
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
    task_list = []
    for t in tasks:
        lead_count = db.query(func.count(Organization.id)).filter(Organization.task_id == t.id).scalar() or 0
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

@router.post("/organizations", status_code=201)
def admin_create_organization(
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "").strip()
    district_name = (payload.get("district") or "").strip()

    if not name or not category or not district_name:
        raise HTTPException(status_code=400, detail="Organization Name, Category, and District are required.")

    # District lookup
    district_obj = db.query(District).filter(District.district_name.ilike(f"%{district_name}%")).first()
    dist_id = district_obj.id if district_obj else None

    # Duplicate check
    existing = db.query(Organization).filter(Organization.name.ilike(name)).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Organization already exists in database with name '{existing.name}' (ID: {existing.id})."
        )

    phone_val = (payload.get("phone") or "").strip()
    if phone_val:
        p_exist = db.query(PhoneNumber).filter(PhoneNumber.normalized_value == phone_val).first()
        if p_exist:
            raise HTTPException(status_code=400, detail=f"Organization with phone '{phone_val}' already exists.")

    email_val = (payload.get("email") or "").strip()
    if email_val:
        e_exist = db.query(EmailAddress).filter(EmailAddress.email.ilike(email_val)).first()
        if e_exist:
            raise HTTPException(status_code=400, detail=f"Organization with email '{email_val}' already exists.")

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

    org = Organization(
        task_id=system_task.id,
        district_id=dist_id,
        name=name,
        category=category,
        district=district_name,
        state=payload.get("state") or "Tamil Nadu",
        city=payload.get("city") or None,
        address=payload.get("address") or None,
        pincode=payload.get("pincode") or None,
        confidence=payload.get("confidence") or "HIGH"
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Optional website
    web_val = (payload.get("website") or "").strip()
    if web_val:
        web = Website(
            organization_id=org.id,
            url=web_val,
            domain=web_val.replace("https://", "").replace("http://", "").split("/")[0],
            status="ACTIVE",
            discovery_source="ADMIN_MANUAL",
            confidence="HIGH"
        )
        db.add(web)

    # Optional phone
    if phone_val:
        pn = PhoneNumber(
            organization_id=org.id,
            raw_value=phone_val,
            normalized_value=phone_val,
            type="office"
        )
        db.add(pn)

    # Optional email
    if email_val:
        em = EmailAddress(
            organization_id=org.id,
            email=email_val,
            extraction_method="admin_manual"
        )
        db.add(em)

    db.commit()
    db.refresh(org)
    return {
        "id": org.id,
        "name": org.name,
        "category": org.category,
        "district": org.district,
        "message": "Master Organization successfully created by Admin."
    }

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
    db.delete(org)
    db.commit()
    return {"message": f"Organization '{org_name}' (ID: {org_id}) deleted successfully."}
