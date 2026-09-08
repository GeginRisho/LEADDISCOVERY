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

        for item in items:
            # Check if campaign was cancelled or paused
            db.refresh(campaign)
            if campaign.status in ("CANCELLED", "PAUSED"):
                break

            item.status = "RUNNING"
            item.started_at = datetime.datetime.utcnow()
            db.commit()

            try:
                # Create dedicated task for this region/category
                task = ScrapingTask(
                    user_id=None,
                    public_task_id=f"CMP-{campaign.id}-{item.id:04d}",
                    location=item.region_name,
                    keyword=item.category,
                    max_results=campaign.max_results_per_region,
                    max_pages_per_site=campaign.max_pages_per_site,
                    status="PENDING"
                )
                db.add(task)
                db.commit()
                db.refresh(task)

                item.task_id = task.id
                db.commit()

                # Execute scraper for this district/category
                await run_scraping_task(task.id)

                # Sync task counters
                sync_task_counters(db, task.id)
                db.refresh(task)

                # Update item counters
                item.status = task.status
                item.discovered_count = task.discovered_count
                item.new_orgs_count = task.new_organizations_count
                item.updated_orgs_count = task.updated_organizations_count
                item.duplicate_count = task.duplicate_count
                item.failed_count = task.failed_count
                item.error_info = task.error_info
                item.completed_at = datetime.datetime.utcnow()
                db.commit()

                # Update campaign aggregates
                campaign.completed_regions += 1
                campaign.discovered_count += task.discovered_count
                campaign.new_orgs_count += task.new_organizations_count
                campaign.updated_orgs_count += task.updated_organizations_count
                campaign.duplicate_count += task.duplicate_count
                campaign.failed_count += task.failed_count
                db.commit()

            except Exception as item_err:
                item.status = "FAILED"
                item.error_info = str(item_err)
                item.completed_at = datetime.datetime.utcnow()
                campaign.failed_regions += 1
                db.commit()
                print(f"[CAMPAIGN ITEM ERROR] Region {item.region_name} failed: {item_err}")
                # Continue to next item (Failure Isolation)

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
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    categories = resolve_categories(payload)
    max_results = payload.get("max_results_per_region", 15)
    max_pages = payload.get("max_pages_per_site", 5)

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

    background_tasks.add_task(run_discovery_campaign, cmp.id)
    return {"message": f"Started Tamil Nadu Campaign across {len(regions)} districts ({total_items} task units).", "campaign_id": cmp.id}

@router.post("/run-puducherry")
def run_puducherry(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    categories = resolve_categories(payload)
    max_results = payload.get("max_results_per_region", 15)
    max_pages = payload.get("max_pages_per_site", 5)

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

    background_tasks.add_task(run_discovery_campaign, cmp.id)
    return {"message": f"Started Puducherry UT Campaign ({len(categories)} categories).", "campaign_id": cmp.id}

@router.post("/run-all")
def run_all_regions(
    payload: dict,
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(run_discovery_campaign, cmp.id)
    return {"message": f"Started Master Regional Campaign across all {len(regions)} regions ({total_items} task units).", "campaign_id": cmp.id}

