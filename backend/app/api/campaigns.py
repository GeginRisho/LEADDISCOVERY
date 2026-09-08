import asyncio
import datetime
import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db, SessionLocal
from app.models.models import (
    User, ScrapingTask, Organization, DiscoveryCampaign, CampaignItem, District
)
from app.api.auth import get_current_admin_user, get_current_user
from app.core.tn_districts import TAMIL_NADU_DISTRICTS, ALL_REGIONS
from app.services.scraper.worker import run_scraping_task, sync_task_counters

from sqlalchemy import func, or_

CATEGORY_TARGETS = {
    "Hotels": 50,
    "Hospitals": 20,
    "Schools": 23,
    "Colleges": 32,
    "Colleges & Universities": 32,
    "Companies": 24,
    "IT Companies": 28
}

def resolve_target_bound(category: str, requested_max: int = 15) -> int:
    cat = (category or "").strip().lower()
    if "hotel" in cat or "resort" in cat:
        return 50
    elif "hospital" in cat or "clinic" in cat:
        return 20
    elif "school" in cat or "cbse" in cat:
        return 23
    elif "college" in cat or "university" in cat:
        return 32
    elif "it" in cat or "software" in cat or "tech" in cat:
        return 28
    elif "company" in cat or "companies" in cat:
        return 24
    return max(requested_max, 15)

router = APIRouter(prefix="/campaigns", tags=["Discovery Campaigns"])

async def run_discovery_campaign(campaign_id: int):
    db: Session = SessionLocal()
    campaign = db.query(DiscoveryCampaign).filter(DiscoveryCampaign.id == campaign_id).first()
    if not campaign:
        db.close()
        return

    campaign.status = "RUNNING"
    campaign.started_at = datetime.datetime.utcnow()
    db.commit()

    try:
        items = db.query(CampaignItem).filter(
            CampaignItem.campaign_id == campaign.id,
            CampaignItem.status.in_(["PENDING", "FAILED", "TIMEOUT"])
        ).order_by(CampaignItem.id.asc()).all()

        semaphore = asyncio.Semaphore(3)

        async def process_item(item_id: int):
            async with semaphore:
                item_db: Session = SessionLocal()
                try:
                    cmp_check = item_db.query(DiscoveryCampaign).filter(DiscoveryCampaign.id == campaign_id).first()
                    if not cmp_check or cmp_check.status in ("CANCELLED", "PAUSED"):
                        return

                    it = item_db.query(CampaignItem).filter(CampaignItem.id == item_id).first()
                    if not it:
                        return

                    it.status = "RUNNING"
                    it.started_at = datetime.datetime.utcnow()
                    item_db.commit()

                    try:
                        from app.core.tn_districts import normalize_district
                        from app.api.organizations import _query_eligible_matrix_counts

                        canon_region = normalize_district(it.region_name)
                        counts_map = _query_eligible_matrix_counts(item_db)
                        reg_counts = counts_map.get(canon_region.lower(), {})

                        cat_key = (it.category or "").lower()
                        if "hotel" in cat_key or "resort" in cat_key:
                            existing_verified_count = reg_counts.get("hotels", 0)
                        elif "hospital" in cat_key or "clinic" in cat_key:
                            existing_verified_count = reg_counts.get("hospitals", 0)
                        elif "school" in cat_key or "cbse" in cat_key:
                            existing_verified_count = reg_counts.get("schools", 0)
                        elif "college" in cat_key or "university" in cat_key:
                            existing_verified_count = reg_counts.get("colleges", 0)
                        elif "it" in cat_key or "software" in cat_key or "tech" in cat_key:
                            existing_verified_count = reg_counts.get("it_companies", 0)
                        elif "company" in cat_key or "companies" in cat_key:
                            existing_verified_count = reg_counts.get("companies", 0)
                        else:
                            existing_verified_count = reg_counts.get("total", 0)

                        target_bound = resolve_target_bound(it.category, cmp_check.max_results_per_region)
                        remaining_target = max(0, target_bound - existing_verified_count)

                        if remaining_target == 0:
                            it.status = "COMPLETED"
                            it.error_info = f"Target of {target_bound} verified organizations already reached ({existing_verified_count} in DB)."
                            it.completed_at = datetime.datetime.utcnow()
                            cmp_check.completed_regions += 1
                            item_db.commit()
                            return

                        # Create dedicated task for remaining target coverage
                        task = ScrapingTask(
                            user_id=None,
                            public_task_id=f"CMP-{cmp_check.id}-{it.id:04d}",
                            location=it.region_name,
                            keyword=it.category,
                            max_results=remaining_target,
                            max_pages_per_site=cmp_check.max_pages_per_site,
                            status="PENDING"
                        )
                        item_db.add(task)
                        item_db.commit()
                        item_db.refresh(task)

                        it.task_id = task.id
                        item_db.commit()

                        # Execute scraper for this district/category
                        await run_scraping_task(task.id)

                        # Sync task counters
                        sync_task_counters(item_db, task.id)
                        item_db.refresh(task)

                        # Update item counters
                        it.status = task.status
                        it.discovered_count = task.discovered_count
                        it.new_orgs_count = task.new_organizations_count
                        it.updated_orgs_count = task.updated_organizations_count
                        it.duplicate_count = task.duplicate_count
                        it.failed_count = task.failed_count
                        it.error_info = task.error_info
                        it.completed_at = datetime.datetime.utcnow()

                        # Update campaign aggregates
                        cmp_check.completed_regions += 1
                        cmp_check.discovered_count += task.discovered_count
                        cmp_check.new_orgs_count += task.new_organizations_count
                        cmp_check.updated_orgs_count += task.updated_organizations_count
                        cmp_check.duplicate_count += task.duplicate_count
                        cmp_check.failed_count += task.failed_count
                        item_db.commit()

                    except Exception as item_err:
                        it.status = "FAILED"
                        it.error_info = str(item_err)
                        it.completed_at = datetime.datetime.utcnow()
                        cmp_check.failed_regions += 1
                        item_db.commit()
                        print(f"[CAMPAIGN ITEM ERROR] Region {it.region_name} failed: {item_err}")
                finally:
                    item_db.close()

        item_tasks = [process_item(item.id) for item in items]
        await asyncio.gather(*item_tasks, return_exceptions=True)

        db.refresh(campaign)
        if campaign.status not in ("CANCELLED", "PAUSED"):
            campaign.status = "COMPLETED"
            campaign.completed_at = datetime.datetime.utcnow()
            db.commit()

    except Exception as cmp_err:
        campaign.status = "FAILED"
        campaign.completed_at = datetime.datetime.utcnow()
        db.commit()
        print(f"[CRITICAL CAMPAIGN FAILURE] Campaign {campaign.id}: {cmp_err}")
    finally:
        db.close()

@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "").strip()
    region_scope = (payload.get("region_scope") or "TAMIL_NADU").upper().strip()
    max_results = payload.get("max_results_per_region", 15)
    max_pages = payload.get("max_pages_per_site", 5)

    if not name or not category:
        raise HTTPException(status_code=400, detail="Campaign Name and Category are required.")

    # Directive 3: Prevent duplicate active campaigns
    running_cmp = db.query(DiscoveryCampaign).filter(
        DiscoveryCampaign.category == category,
        DiscoveryCampaign.region_scope == region_scope,
        DiscoveryCampaign.status == "RUNNING"
    ).first()

    if running_cmp:
        raise HTTPException(
            status_code=400,
            detail=f"A campaign for '{category}' in scope '{region_scope}' is already running (Campaign ID: {running_cmp.id})."
        )

    # Determine region list
    if region_scope == "TAMIL_NADU":
        regions = [d["name"] for d in TAMIL_NADU_DISTRICTS]
    elif region_scope == "PUDUCHERRY":
        regions = ["Puducherry"]
    else: # ALL
        regions = [d["name"] for d in ALL_REGIONS]

    campaign = DiscoveryCampaign(
        name=name,
        region_scope=region_scope,
        category=category,
        max_results_per_region=max_results,
        max_pages_per_site=max_pages,
        status="PENDING",
        total_regions=len(regions)
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Create CampaignItems
    for reg_name in regions:
        item = CampaignItem(
            campaign_id=campaign.id,
            region_name=reg_name,
            category=category,
            status="PENDING"
        )
        db.add(item)
    db.commit()
    db.refresh(campaign)

    # Auto-start if requested
    if payload.get("auto_start", True):
        background_tasks.add_task(run_discovery_campaign, campaign.id)

    return campaign

@router.get("")
def list_campaigns(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    campaigns = db.query(DiscoveryCampaign).order_by(DiscoveryCampaign.created_at.desc()).all()
    return campaigns

@router.get("/{campaign_id}")
def get_campaign_detail(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    campaign = db.query(DiscoveryCampaign).options(
        joinedload(DiscoveryCampaign.items)
    ).filter(DiscoveryCampaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign

@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    campaign = db.query(DiscoveryCampaign).filter(DiscoveryCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if campaign.status == "RUNNING":
        raise HTTPException(status_code=400, detail="Campaign is already running.")

    background_tasks.add_task(run_discovery_campaign, campaign.id)
    return {"message": f"Campaign '{campaign.name}' (ID: {campaign.id}) started successfully."}

@router.post("/{campaign_id}/pause")
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    campaign = db.query(DiscoveryCampaign).filter(DiscoveryCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    campaign.status = "PAUSED"
    db.commit()
    return {"message": f"Campaign '{campaign.name}' paused."}

@router.post("/{campaign_id}/resume")
def resume_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    campaign = db.query(DiscoveryCampaign).filter(DiscoveryCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if campaign.status == "RUNNING":
        raise HTTPException(status_code=400, detail="Campaign is already running.")

    campaign.status = "PENDING"
    db.commit()
    background_tasks.add_task(run_discovery_campaign, campaign.id)
    return {"message": f"Resuming campaign '{campaign.name}' (ID: {campaign.id}). Remaining items will be processed."}

CONFIGURED_CATEGORIES = [
    "Colleges & Universities",
    "Schools",
    "Hotels",
    "Hospitals",
    "Companies",
    "IT Companies"
]

def resolve_categories(payload: dict) -> List[str]:
    cats = payload.get("categories")
    if isinstance(cats, list) and cats:
        return [str(c).strip() for c in cats if str(c).strip()]
    single_cat = payload.get("category")
    if single_cat:
        return [str(single_cat).strip()]
    return CONFIGURED_CATEGORIES

@router.post("/run-all-tn")
def run_all_tamil_nadu(
    payload: dict = {},
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    categories = resolve_categories(payload or {})
    max_results = (payload or {}).get("max_results_per_region", 15)
    max_pages = (payload or {}).get("max_pages_per_site", 5)

    regions = [d["name"] for d in TAMIL_NADU_DISTRICTS]
    total_items = len(regions) * len(categories)
    
    cmp = DiscoveryCampaign(
        name=f"Tamil Nadu Campaign ({', '.join(categories[:2])}{'...' if len(categories)>2 else ''})",
        region_scope="TAMIL_NADU",
        category=", ".join(categories),
        max_results_per_region=max_results,
        max_pages_per_site=max_pages,
        status="PENDING",
        total_regions=total_items
    )
    db.add(cmp)
    db.commit()
    db.refresh(cmp)

    for reg_name in regions:
        for cat in categories:
            item = CampaignItem(
                campaign_id=cmp.id,
                region_name=reg_name,
                category=cat,
                status="PENDING"
            )
            db.add(item)
    db.commit()

    if background_tasks:
        background_tasks.add_task(run_discovery_campaign, cmp.id)
    return {"message": f"Started Tamil Nadu Campaign across {len(regions)} districts ({total_items} task units).", "campaign_id": cmp.id}

@router.post("/run-puducherry")
def run_puducherry(
    payload: dict = {},
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    categories = resolve_categories(payload or {})
    max_results = (payload or {}).get("max_results_per_region", 15)
    max_pages = (payload or {}).get("max_pages_per_site", 5)

    cmp = DiscoveryCampaign(
        name=f"Puducherry UT Campaign ({', '.join(categories[:2])}{'...' if len(categories)>2 else ''})",
        region_scope="PUDUCHERRY",
        category=", ".join(categories),
        max_results_per_region=max_results,
        max_pages_per_site=max_pages,
        status="PENDING",
        total_regions=len(categories)
    )
    db.add(cmp)
    db.commit()
    db.refresh(cmp)

    for cat in categories:
        item = CampaignItem(
            campaign_id=cmp.id,
            region_name="Puducherry",
            category=cat,
            status="PENDING"
        )
        db.add(item)
    db.commit()

    if background_tasks:
        background_tasks.add_task(run_discovery_campaign, cmp.id)
    return {"message": f"Started Puducherry UT Campaign ({len(categories)} categories).", "campaign_id": cmp.id}

@router.post("/run-all")
def run_all_regions(
    payload: dict = {},
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    categories = resolve_categories(payload)
    max_results = payload.get("max_results_per_region", 15)
    max_pages = payload.get("max_pages_per_site", 5)

    regions = [d["name"] for d in ALL_REGIONS]
    total_items = len(regions) * len(categories)

    cmp = DiscoveryCampaign(
        name=f"All Regions Campaign (38 TN + Puducherry UT)",
        region_scope="ALL",
        category=", ".join(categories),
        max_results_per_region=max_results,
        max_pages_per_site=max_pages,
        status="PENDING",
        total_regions=total_items
    )
    db.add(cmp)
    db.commit()
    db.refresh(cmp)

    for reg_name in regions:
        for cat in categories:
            item = CampaignItem(
                campaign_id=cmp.id,
                region_name=reg_name,
                category=cat,
                status="PENDING"
            )
            db.add(item)
    db.commit()

    if background_tasks:
        background_tasks.add_task(run_discovery_campaign, cmp.id)
    return {"message": f"Started Master Regional Campaign across all {len(regions)} regions ({total_items} task units).", "campaign_id": cmp.id}

