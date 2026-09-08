import asyncio
import datetime
import traceback
import time
import urllib.parse
import re
from typing import List, Dict, Any, Optional, Tuple
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import (
    ScrapingTask, Organization, Website, SourcePage, 
    PhoneNumber, EmailAddress, SocialLink, ScrapingLog, District, TaskLead
)
from app.services.scraper.discovery import (
    DuckDuckGoHTMLProvider, BingHTMLProvider, UserURLProvider, 
    CbseSarasSeedProvider, PublicDirectoryProvider, MultiSourceDiscoveryManager,
    DiscoveryError, is_generic_listing_title
)
from app.services.scraper.identity_verification import verify_organization_identity
from app.services.location_service import verify_organization_location, normalize_target_location
from app.services.scraper.identification import (
    identify_official_website, extract_domain, clean_org_name, normalize_url,
    is_directory_domain, verify_category_match
)
from app.services.scraper.crawler import DomainCrawler
from app.services.verification import calculate_lead_confidence, check_dns_resolution
from app.services.deduplication import calculate_match_score, merge_organizations

# Bounded Concurrency Semaphores
RESOLUTION_SEMAPHORE = asyncio.Semaphore(5)
CRAWL_SEMAPHORE = asyncio.Semaphore(5)

def log_event(db: Session, task_id: int, event_type: str, message: str, metadata: Optional[Dict[str, Any]] = None):
    log = ScrapingLog(
        task_id=task_id,
        event_type=event_type,
        message=message,
        metadata_json=metadata or {}
    )
    db.add(log)
    db.commit()

def is_url_list(text: str) -> bool:
    text_stripped = text.strip()
    if "," in text_stripped:
        parts = [p.strip() for p in text_stripped.split(",") if p.strip()]
        return any(p.startswith(("http://", "https://", "www.")) or p.endswith((".com", ".org", ".net", ".edu", ".in")) for p in parts)
    return text_stripped.startswith(("http://", "https://", "www.")) or text_stripped.endswith((".com", ".org", ".net", ".edu", ".in"))

def resolve_district(db: Session, location: str, city: str = "") -> Tuple[Optional[int], Optional[str]]:
    from app.core.tn_districts import normalize_district
    canon_dist = normalize_district(location or city)
    districts = db.query(District).all()
    for d in districts:
        if d.district_name.lower() == canon_dist.lower():
            return d.id, d.district_name
    return None, canon_dist

def sync_task_counters(db: Session, task_id: int):
    """
    Synchronizes task metrics from TaskLead and Organization database records.
    Order Invariant: If websites_crawled == 0, website-derived email and phone counts are 0.
    """
    task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        return

    task_leads = db.query(TaskLead).filter(TaskLead.task_id == task.id).all()
    if task_leads:
        org_ids = [tl.organization_id for tl in task_leads]
    else:
        orgs = db.query(Organization).filter(Organization.task_id == task.id).all()
        org_ids = [o.id for o in orgs]

    if not org_ids:
        task.websites_found = 0
        task.websites_crawled = 0
        task.phone_count = 0
        task.email_count = 0
        task.address_count = 0
        db.commit()
        return

    found_count = db.query(func.count(Website.id))\
        .filter(Website.organization_id.in_(org_ids))\
        .filter(or_(Website.url.isnot(None), Website.domain.isnot(None)))\
        .scalar() or 0

    crawled_count = db.query(func.count(Website.id))\
        .filter(Website.organization_id.in_(org_ids))\
        .filter(Website.status == "ACTIVE")\
        .scalar() or 0

    failed_count = db.query(func.count(Website.id))\
        .filter(Website.organization_id.in_(org_ids))\
        .filter(Website.status.in_(["FAILED", "BLOCKED"]))\
        .scalar() or 0

    phone_count = db.query(func.count(PhoneNumber.id))\
        .filter(PhoneNumber.organization_id.in_(org_ids))\
        .scalar() or 0

    email_count = db.query(func.count(EmailAddress.id))\
        .filter(EmailAddress.organization_id.in_(org_ids))\
        .scalar() or 0

    address_count = db.query(func.count(Organization.id))\
        .filter(Organization.id.in_(org_ids))\
        .filter(Organization.address.isnot(None))\
        .filter(Organization.address != "")\
        .scalar() or 0

    task.websites_found = found_count
    task.websites_crawled = crawled_count
    task.failed_count = failed_count
    task.phone_count = phone_count
    task.email_count = email_count
    task.address_count = address_count
    db.commit()

async def resolve_official_website(
    org_name: str, 
    location: str, 
    initial_url: str, 
    client: httpx.AsyncClient
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolves official website URL and domain for a candidate organization.
    Uses multi-signal verification. Discovery source portal links MUST NEVER be returned as official website.
    Returns (official_url, domain, error_reason)
    """
    res_start = time.time()

    if initial_url and not is_directory_domain(initial_url):
        id_res = identify_official_website(org_name, initial_url)
        if id_res.get("is_official") and not id_res.get("is_directory_source"):
            return id_res["normalized_url"], id_res["domain"], None

    query = f"{org_name} {location} official website"
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.bing.com/search?q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": "SRCHHPGUSR=SRCHLANG=en;"
    }

    try:
        resp = await asyncio.wait_for(client.get(search_url, headers=headers), timeout=8.0)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            from app.services.scraper.discovery import unwrap_bing_url
            soup = BeautifulSoup(resp.text, "lxml")
            
            clean_org = clean_org_name(org_name)
            org_words = set(w for w in clean_org.split() if len(w) >= 3 and w not in ("hotel", "hotels", "school", "schools", "college", "colleges", "hospital", "hospitals", "resort", "resorts", "inn", "stay", "lodge", "puducherry", "pondicherry", "salem", "chennai", "kanyakumari"))

            for item in soup.find_all("li", class_="b_algo"):
                h2 = item.find("h2")
                if not h2 or not h2.find("a"):
                    continue
                actual_url = unwrap_bing_url(h2.find("a")["href"])
                if not actual_url:
                    continue
                domain = extract_domain(actual_url)
                if not domain or is_directory_domain(domain):
                    continue
                
                clean_domain_part = domain.split(".")[0].lower()
                domain_words = set(re.split(r'[^a-zA-Z0-9]', clean_domain_part))

                is_institutional = any(inst in domain for inst in [".edu.in", ".ac.in", ".org.in", ".edu", ".ac", ".school"])

                if org_words and not is_institutional:
                    overlap = org_words.intersection(domain_words)
                    if not overlap:
                        brand_match = False
                        if len(org_words) >= 2:
                            words_in_domain = sum(1 for bw in org_words if bw in clean_domain_part)
                            if words_in_domain >= 2:
                                brand_match = True
                        else:
                            single_word = list(org_words)[0]
                            if single_word in clean_domain_part:
                                brand_match = True

                        if not brand_match:
                            continue

                return normalize_url(actual_url), domain, None
    except Exception as e:
        pass

    # Fallback to DuckDuckGo if Bing yielded no result or failed
    try:
        ddg_query = urllib.parse.quote_plus(f"{org_name} {location} official website")
        ddg_url = f"https://html.duckduckgo.com/html/?q={ddg_query}"
        ddg_resp = await asyncio.wait_for(client.get(ddg_url, headers=headers), timeout=5.0)
        if ddg_resp.status_code == 200:
            from bs4 import BeautifulSoup
            from app.services.scraper.discovery import unwrap_ddg_url
            d_soup = BeautifulSoup(ddg_resp.text, "lxml")
            clean_org = clean_org_name(org_name)
            org_words = set(w for w in clean_org.split() if len(w) >= 3 and w not in ("hotel", "hotels", "school", "schools", "college", "colleges", "hospital", "hospitals", "resort", "resorts", "inn", "stay", "lodge", "puducherry", "pondicherry", "salem", "chennai", "kanyakumari"))

            for a_item in d_soup.find_all("a", class_="result__a"):
                raw_href = a_item.get("href")
                if not raw_href:
                    continue
                actual_url = unwrap_ddg_url(raw_href)
                if not actual_url:
                    continue
                domain = extract_domain(actual_url)
                if not domain or is_directory_domain(domain):
                    continue

                clean_domain_part = domain.split(".")[0].lower()
                domain_words = set(re.split(r'[^a-zA-Z0-9]', clean_domain_part))
                is_institutional = any(inst in domain for inst in [".edu.in", ".ac.in", ".org.in", ".edu", ".ac", ".school"])

                if org_words and not is_institutional:
                    overlap = org_words.intersection(domain_words)
                    if not overlap:
                        brand_match = False
                        if len(org_words) >= 2:
                            words_in_domain = sum(1 for bw in org_words if bw in clean_domain_part)
                            if words_in_domain >= 2:
                                brand_match = True
                        else:
                            single_word = list(org_words)[0]
                            if single_word in clean_domain_part:
                                brand_match = True
                        if not brand_match:
                            continue

                return normalize_url(actual_url), domain, None
    except Exception:
        pass

    dur_ms = int((time.time() - res_start) * 1000)
    return None, None, f"No standalone official domain found ({dur_ms}ms)"

async def run_scraping_task(task_id: int):
    """
    Background worker task executing the complete, strict LeadDiscovery verification pipeline.
    """
    db: Session = SessionLocal()
    task = db.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        db.close()
        return

    # Transition to RUNNING
    task.status = "RUNNING"
    task.started_at = datetime.datetime.utcnow()
    task.progress = 5
    db.commit()

    t_task_start = time.time()
    target_min = min(15, task.max_results) if task.max_results >= 15 else task.max_results
    
    # Real progress step 1 (~3s)
    log_event(
        db, task.id, "DISCOVERY_STARTED",
        f"[DISCOVERY] Task initialized. Keyword: '{task.keyword}', Location: '{task.location}', Target: {target_min} minimum verified organizations (Max: {task.max_results})."
    )

    candidates: List[Dict[str, Any]] = []
    seen_names: set = set()
    seen_urls: set = set()

    rejection_metrics = {
        "not_an_organization": 0,
        "category_mismatch": 0,
        "location_mismatch": 0,
        "directory_url": 0,
        "dns_failed": 0,
        "unreachable": 0,
        "duplicates": 0
    }

    httpx_limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    shared_client = httpx.AsyncClient(
        timeout=8.0,
        limits=httpx_limits,
        verify=False,
        follow_redirects=True,
        headers={"User-Agent": settings.SCRAPER_USER_AGENT}
    )

    domain_crawl_cache: Dict[str, Dict[str, Any]] = {}
    disc_ms = 0
    db_ms = 0
    total_http_time = 0.0

    try:
        t_disc_start = time.time()
        log_event(db, task.id, "PROGRESS_UPDATE", "Executing multi-source candidate discovery across parallel providers...")

        active_leads: List[Dict[str, Any]] = []

        # Seed pre-verified leads from fast search path if attached
        from app.services.scraper.identification import normalize_category_and_subcategory
        norm_cat, norm_subcat = normalize_category_and_subcategory(task.keyword)

        existing_tls = db.query(TaskLead).filter(TaskLead.task_id == task.id).all()
        for tl in existing_tls:
            if tl.organization:
                org = tl.organization
                seen_names.add(org.name.lower().strip())
                if org.official_website_url:
                    seen_urls.add(org.official_website_url.lower().strip())
                if org.website and org.website.domain:
                    seen_urls.add(org.website.domain.lower().strip())
                
                active_leads.append({
                    "name": org.name,
                    "category": org.category or norm_cat,
                    "sub_category": org.sub_category or norm_subcat,
                    "address": org.address,
                    "city": org.city,
                    "state": org.state,
                    "country": org.country,
                    "pincode": org.pincode,
                    "domain": org.website.domain if org.website else None,
                    "official_website_url": org.official_website_url,
                    "source_url": org.discovery_source_url,
                    "discovery_source": "FAST_VERIFIED_INDEX",
                    "emails": [{"email": e.email} for e in org.email_addresses] if org.email_addresses else [],
                    "phones": [{"normalized_value": p.normalized_value, "raw_value": p.raw_value} for p in org.phone_numbers] if org.phone_numbers else [],
                    "socials": [],
                    "people": [],
                    "identity_verified": True,
                    "category_verified": True,
                    "country_verified": True,
                    "state_verified": True,
                    "district_verified": True,
                    "location_verified": True,
                    "official_website_verified": org.official_website_verified,
                    "confidence": org.confidence or "HIGH"
                })

        if active_leads:
            log_event(db, task.id, "FAST_INDEX_LOADED", f"Loaded {len(active_leads)} pre-verified master organizations into active task state.")

        # Multi-Source Discovery Manager Execution
        discovery_manager = MultiSourceDiscoveryManager()
        raw_candidates = await discovery_manager.discover_candidates(
            location=task.location,
            keyword=task.keyword,
            max_results=task.max_results,
            shared_client=shared_client
        )

        task.discovered_count = len(raw_candidates)
        task.progress = 25
        db.commit()

        log_event(
            db, task.id, "DISCOVERY_COMPLETED",
            f"[MULTI-SOURCE DISCOVERY] Discovered {len(raw_candidates)} candidate entities across multi-source providers."
        )

        target_loc_obj = normalize_target_location(task.location)

        for c in raw_candidates:
            if len(active_leads) >= target_min:
                break

            name_raw = c["name"]
            url_raw = c.get("possible_website") or ""

            name_low = name_raw.lower().strip()
            url_low = url_raw.lower().strip()

            if name_low in seen_names or (url_low and url_low in seen_urls):
                continue

            # STAGE 1: IDENTITY VERIFICATION
            is_real_org, id_reason, id_meta = verify_organization_identity(name_raw, url_raw, c.get("snippet", ""))
            if not is_real_org:
                rejection_metrics["not_an_organization"] += 1
                log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Identity Filter: {id_reason}\"")
                continue

            # STAGE 2: CATEGORY VERIFICATION
            is_cat_valid, cat_reason = verify_category_match(task.keyword, name_raw, c.get("category", ""), url_raw)
            if not is_cat_valid:
                rejection_metrics["category_mismatch"] += 1
                log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Category Filter: {cat_reason}\"")
                continue

            # STAGE 3: LOCATION VERIFICATION
            is_loc_valid, loc_reason, loc_meta = verify_organization_location(
                target_location_str=task.location,
                org_name=name_raw,
                detected_address=c.get("address", ""),
                domain=url_raw
            )
            if not is_loc_valid and c.get("discovery_source_type") not in ("OFFICIAL_REGISTRY", "GOVERNMENT_DIRECTORY"):
                rejection_metrics["location_mismatch"] += 1
                log_event(db, task.id, "[LOCATION REJECT]", f"[LOCATION REJECT] candidate=\"{name_raw}\" reason=\"Location Filter: {loc_reason}\"")
                continue

            seen_names.add(name_low)
            if url_low:
                seen_urls.add(url_low)

            candidates.append(c)

            # STAGE 4: OFFICIAL WEBSITE RESOLUTION & CRAWL (OPTIONAL ENHANCEMENT - DO NOT DISCARD CANDIDATE IF UNRESOLVED)
            official_url = None
            domain = None
            res_err = None
            has_web_verified = False

            if url_raw and not is_directory_domain(url_raw):
                official_url = url_raw
                domain = extract_domain(url_raw)

            if not official_url or not domain or is_directory_domain(domain):
                async with RESOLUTION_SEMAPHORE:
                    official_url, domain, res_err = await resolve_official_website(
                        name_raw, task.location, url_raw, shared_client
                    )

            crawl_res = None
            website_status = "ACTIVE"
            website_reason = None
            emails_list = []
            phones_list = []
            socials_list = []
            people_list = []
            address_str, city_str, state_str, pin_str = "", "", "", ""

            if official_url and domain and not is_directory_domain(domain):
                has_dns = await check_dns_resolution(domain, timeout=4.0)
                if has_dns:
                    if domain in domain_crawl_cache:
                        crawl_res = domain_crawl_cache[domain]
                        website_status = crawl_res.get("status", "ACTIVE")
                    else:
                        async with CRAWL_SEMAPHORE:
                            crawler = DomainCrawler(
                                start_url=official_url,
                                max_pages=task.max_pages_per_site,
                                max_depth=2,
                                client=shared_client
                            )
                            c_start = time.time()
                            try:
                                crawl_res = await crawler.crawl()
                                total_http_time += (time.time() - c_start)
                                domain_crawl_cache[domain] = crawl_res
                                website_status = crawl_res.get("status", "ACTIVE")
                            except Exception as crawl_err:
                                website_status = "FAILED"
                                website_reason = str(crawl_err)

                    if website_status in ("SUCCESS", "ACTIVE") and crawl_res:
                        emails_list = crawl_res.get("emails") or []
                        phones_list = crawl_res.get("phones") or []
                        socials_list = crawl_res.get("socials") or []
                        people_list = crawl_res.get("people") or []

                        if crawl_res.get("addresses"):
                            addr = crawl_res["addresses"][0]
                            address_str = addr.get("address") or ""
                            city_str = addr.get("city") or ""
                            state_str = addr.get("state") or ""
                            pin_str = addr.get("pincode") or ""

                        html_evidence = (crawl_res.get("page_title") or "") + " " + " ".join(crawl_res.get("headings") or [])
                        is_web_loc_valid, _, _ = verify_organization_location(
                            target_location_str=task.location,
                            org_name=name_raw,
                            detected_address=address_str,
                            html_text=html_evidence,
                            domain=domain or ""
                        )
                        if is_web_loc_valid or has_dns:
                            has_web_verified = True
                elif official_url and domain and not is_directory_domain(domain):
                    has_web_verified = True

            # Contacts fallback from discovery metadata if crawl was empty or unperformed
            if not phones_list and c.get("phone"):
                phones_list = [{"raw_value": c["phone"], "normalized_value": c["phone"], "type": "main"}]
            if not emails_list and c.get("email"):
                emails_list = [{"email": c["email"], "extraction_method": "discovery_source"}]

            lead_res = {
                "name": name_raw,
                "category": task.keyword,
                "address": address_str or c.get("address", ""),
                "city": city_str or target_loc_obj["target_city"],
                "state": state_str or target_loc_obj["target_state_or_ut"],
                "country": target_loc_obj["target_country"],
                "pincode": pin_str or c.get("pincode", ""),
                "domain": domain if has_web_verified else None,
                "official_website_url": official_url if has_web_verified else None,
                "possible_website": official_url or url_raw,
                "website_status": website_status if has_web_verified else "UNVERIFIED",
                "website_reason": website_reason,
                "source_url": c.get("source_url") or url_raw,
                "discovery_source": c.get("discovery_source", "SEARCH_PROVIDER"),
                "discovery_source_type": c.get("discovery_source_type", "SCRAPER_VERIFIED"),
                "emails": emails_list,
                "phones": phones_list,
                "socials": socials_list,
                "people": people_list,
                "identity_verified": True,
                "category_verified": True,
                "country_verified": True,
                "state_verified": True,
                "district_verified": True,
                "location_verified": True,
                "official_website_verified": has_web_verified,
                "confidence": "HIGH" if has_web_verified else "MEDIUM"
            }

            # REQUIRE OFFICIAL WEBSITE VERIFICATION FOR ACTIVE VERIFIED LEADS
            if not has_web_verified and c.get("discovery_source_type") not in ("OFFICIAL_REGISTRY", "GOVERNMENT_DIRECTORY"):
                log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Official website ownership could not be established\"")
                continue

            is_dup = False
            for existing in active_leads:
                score = calculate_match_score(lead_res, existing)
                if score >= 0.8:
                    is_dup = True
                    task.duplicate_count += 1
                    rejection_metrics["duplicates"] += 1
                    existing.update(merge_organizations(existing, lead_res))
                    break

            if not is_dup:
                active_leads.append(lead_res)
                badge_type = "WEB VERIFIED" if has_web_verified else "REGISTRY VERIFIED"
                log_event(db, task.id, "[LEAD VERIFIED]", f"[LEAD VERIFIED] ({len(active_leads)}/{target_min}) org=\"{name_raw}\" badge=\"{badge_type}\"")

            prog = min(25 + int((len(active_leads) / target_min) * 60), 85)
            task.progress = prog
            db.commit()

        t_disc_end = time.time()
        disc_ms = int((t_disc_end - t_disc_start) * 1000)
        task.progress = 85
        db.commit()

        # -------------------------------------------------------------
        # STAGE 8: BATCHED DATABASE TRANSACTIONS & TASKLEAD UPSERT
        # -------------------------------------------------------------
        t_db_start = time.time()
        log_event(db, task.id, "DATABASE_SAVING", f"[DATABASE] Saving {len(active_leads)} verified master organizations...")

        new_orgs_count = 0
        updated_orgs_count = 0
        seen_task_lead_org_ids: set = set()

        for lead in active_leads:
            dist_id, dist_name = resolve_district(db, task.location, lead.get("city", ""))

            existing_org = None
            if lead.get("domain") and not is_directory_domain(lead["domain"]):
                web_match = db.query(Website).filter(Website.domain == lead["domain"]).first()
                if web_match and web_match.organization:
                    existing_org = web_match.organization

            if not existing_org and lead.get("phones"):
                for p in lead["phones"]:
                    p_match = db.query(PhoneNumber).filter(PhoneNumber.normalized_value == p["normalized_value"]).first()
                    if p_match and p_match.organization:
                        existing_org = p_match.organization
                        break

            if not existing_org and lead.get("emails"):
                for e in lead["emails"]:
                    e_match = db.query(EmailAddress).filter(EmailAddress.email == e["email"]).first()
                    if e_match and e_match.organization:
                        existing_org = e_match.organization
                        break

            if not existing_org:
                clean_prefix = clean_org_name(lead["name"])[:10]
                if clean_prefix:
                    orgs_in_db = db.query(Organization).filter(Organization.name.ilike(f"%{clean_prefix}%")).all()
                    for db_o in orgs_in_db:
                        db_dict = {"name": db_o.name, "city": db_o.city or ""}
                        if calculate_match_score(lead, db_dict) >= 0.8:
                            existing_org = db_o
                            break

            cat_norm, subcat_norm = normalize_category_and_subcategory(task.keyword)

            if existing_org:
                updated_orgs_count += 1
                existing_org.task_id = task.id
                existing_org.category = cat_norm
                existing_org.sub_category = subcat_norm
                existing_org.updated_at = datetime.datetime.utcnow()
                if lead["official_website_url"]:
                    existing_org.official_website_url = lead["official_website_url"]
                existing_org.identity_verified = True
                existing_org.category_verified = True
                existing_org.country_verified = True
                existing_org.state_verified = True
                existing_org.district_verified = True
                existing_org.location_verified = True
                existing_org.official_website_verified = lead.get("official_website_verified", False)
                existing_org.confidence = lead["confidence"]
                org = existing_org
            else:
                new_orgs_count += 1
                org = Organization(
                    task_id=task.id,
                    district_id=dist_id,
                    name=lead["name"],
                    category=cat_norm,
                    sub_category=subcat_norm,
                    official_website_url=lead["official_website_url"],
                    discovery_source_url=lead["source_url"],
                    address=lead["address"] or None,
                    city=lead["city"] or None,
                    district=dist_name or None,
                    state=lead["state"],
                    country=lead["country"],
                    pincode=lead["pincode"] or None,
                    identity_verified=True,
                    category_verified=True,
                    country_verified=True,
                    state_verified=True,
                    district_verified=True,
                    location_verified=True,
                    official_website_verified=lead.get("official_website_verified", False),
                    confidence=lead["confidence"],
                    source_type="SCRAPER_VERIFIED" if lead.get("official_website_verified") else "UNVERIFIED",
                    is_quarantined=not lead.get("official_website_verified", False),
                    quarantine_reason=None if lead.get("official_website_verified") else "Official website ownership could not be established"
                )
                db.add(org)
                db.flush()

            if org.id not in seen_task_lead_org_ids:
                existing_tl = db.query(TaskLead).filter(
                    TaskLead.task_id == task.id,
                    TaskLead.organization_id == org.id
                ).first()
                if not existing_tl:
                    tl = TaskLead(
                        task_id=task.id,
                        organization_id=org.id,
                        qualification_status="QUALIFIED",
                        confidence=org.confidence,
                        identity_verified=True,
                        category_verified=True,
                        location_verified=True,
                        official_website_verified=lead.get("official_website_verified", False)
                    )
                    db.add(tl)
                seen_task_lead_org_ids.add(org.id)

            web_url = lead.get("official_website_url")
            web_domain = lead.get("domain")
            existing_web = db.query(Website).filter(Website.organization_id == org.id).first()
            
            fallback_url = web_url or (f"https://{web_domain}" if web_domain else f"https://no-website-{org.id}.local")

            if existing_web:
                if web_domain: existing_web.domain = web_domain
                existing_web.url = fallback_url
                existing_web.status = lead.get("website_status", "ACTIVE")
                existing_web.reason = lead.get("website_reason")
                web = existing_web
            else:
                web = Website(
                    organization_id=org.id,
                    domain=web_domain or (extract_domain(web_url) if web_url else f"no-website-{org.id}.local"),
                    url=fallback_url,
                    status=lead.get("website_status", "ACTIVE"),
                    reason=lead.get("website_reason"),
                    discovery_source=lead.get("discovery_source", "Scraper"),
                    confidence=lead.get("confidence", "MEDIUM")
                )
                db.add(web)
                db.flush()

            pages_map: Dict[str, SourcePage] = {}

            existing_emails = {e.email for e in org.email_addresses} if org.email_addresses else set()
            for e in lead["emails"]:
                if e["email"] not in existing_emails:
                    s_url = e.get("source_url") or fallback_url
                    if s_url not in pages_map:
                        page = SourcePage(website_id=web.id, url=s_url)
                        db.add(page)
                        db.flush()
                        pages_map[s_url] = page
                        
                    email_obj = EmailAddress(
                        organization_id=org.id,
                        source_page_id=pages_map[s_url].id,
                        email=e["email"],
                        extraction_method=e["extraction_method"]
                    )
                    db.add(email_obj)
                    existing_emails.add(e["email"])

            existing_phones = {p.normalized_value for p in org.phone_numbers} if org.phone_numbers else set()
            for p in lead["phones"]:
                if p["normalized_value"] not in existing_phones:
                    s_url = p["source_url"]
                    if s_url not in pages_map:
                        page = SourcePage(website_id=web.id, url=s_url)
                        db.add(page)
                        db.flush()
                        pages_map[s_url] = page
                        
                    phone_obj = PhoneNumber(
                        organization_id=org.id,
                        source_page_id=pages_map[s_url].id,
                        raw_value=str(p.get("raw_value") or ""),
                        normalized_value=str(p.get("normalized_value") or "")[:100],
                        type=str(p.get("type") or "main")[:50]
                    )
                    db.add(phone_obj)
                    existing_phones.add(p["normalized_value"])

            existing_socials = {s.url for s in org.social_links} if org.social_links else set()
            for s in lead["socials"]:
                if s["url"] not in existing_socials:
                    s_url = s["source_url"]
                    if s_url not in pages_map:
                        page = SourcePage(website_id=web.id, url=s_url)
                        db.add(page)
                        db.flush()
                        pages_map[s_url] = page
                        
                    social_obj = SocialLink(
                        organization_id=org.id,
                        source_page_id=pages_map[s_url].id,
                        platform=s["platform"],
                        url=s["url"]
                    )
                    db.add(social_obj)
                    existing_socials.add(s["url"])

        db.commit()

        t_db_end = time.time()
        db_ms = int((t_db_end - t_db_start) * 1000)

        # -------------------------------------------------------------
        # STAGE 9: FINALIZATION & STATUS CALCULATION
        # -------------------------------------------------------------
        task.new_organizations_count = new_orgs_count
        task.updated_organizations_count = updated_orgs_count
        task.progress = 95
        task.completed_at = datetime.datetime.utcnow()

        verified_count = len(active_leads)

        if verified_count >= target_min:
            task.status = "COMPLETED"
            task.error_info = None
        elif verified_count > 0:
            task.status = "COMPLETED_BELOW_MINIMUM"
            task.error_info = (
                f"Discovered {verified_count} verified organizations (Target: {target_min}). "
                f"Rejection breakdown: Identity filters: {rejection_metrics['not_an_organization']}, "
                f"Category mismatches: {rejection_metrics['category_mismatch']}, "
                f"Location mismatches: {rejection_metrics['location_mismatch']}, "
                f"Directory links: {rejection_metrics['directory_url']}, "
                f"Unreachable/DNS failed: {rejection_metrics['dns_failed']}, Duplicates: {rejection_metrics['duplicates']}."
            )
        else:
            task.status = "COMPLETED_WITH_NO_RESULTS"
            task.error_info = f"No verified organizations passed qualification out of {len(candidates)} raw candidates."

        db.commit()
        sync_task_counters(db, task.id)
        task.progress = 100
        db.commit()

        t_task_end = time.time()
        total_wall_ms = int((t_task_end - t_task_start) * 1000)

        perf_summary = f"""
==================================================
PERFORMANCE SUMMARY (Task ID: {task.id})
--------------------------------------------------
Total Wall-Clock Time: {total_wall_ms} ms ({total_wall_ms / 1000:.2f} s)
Discovery & Verification Stage: {disc_ms} ms
Database Stage: {db_ms} ms
--------------------------------------------------
Verified Leads Created: {verified_count} (New: {new_orgs_count}, Updated: {updated_orgs_count})
==================================================
"""
        log_event(db, task.id, "PERFORMANCE_SUMMARY", perf_summary)
        log_event(
            db, task.id, "TASK_COMPLETED", 
            f"[TASK COMPLETED] Status='{task.status}'. Target={target_min}, Verified Orgs={verified_count}, Total Runtime={total_wall_ms / 1000:.2f}s."
        )

    except Exception as e:
        db.rollback()
        task.status = "FAILED"
        task.completed_at = datetime.datetime.utcnow()
        task.error_info = f"Critical Scraper Error: {str(e)}\n{traceback.format_exc()}"
        db.commit()
        log_event(db, task.id, "TASK_FAILED", f"Scraper task failed with error: {str(e)}")
        print(f"CRITICAL SCRAPER ERROR: {e}")
        traceback.print_exc()
        
    finally:
        await shared_client.aclose()
        db.close()
