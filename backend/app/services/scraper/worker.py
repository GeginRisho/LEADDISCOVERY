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
    CbseSarasSeedProvider, PublicDirectoryProvider, DiscoveryError, is_generic_listing_title
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
    districts = db.query(District).all()
    loc_clean = (location or "").lower().strip()
    city_clean = (city or "").lower().strip()
    
    for d in districts:
        d_name_low = d.district_name.lower()
        if d_name_low in loc_clean or loc_clean in d_name_low or (city_clean and (d_name_low in city_clean or city_clean in d_name_low)):
            return d.id, d.district_name
    return None, location

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
        dur_ms = int((time.time() - res_start) * 1000)
        return None, None, f"Website resolution timeout/error after {dur_ms}ms: {str(e)}"

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
        log_event(db, task.id, "PROGRESS_UPDATE", "Discovering candidate organizations across bounded providers...")

        if is_url_list(task.location):
            providers = [("UserURLProvider", UserURLProvider())]
        else:
            providers = [
                ("CbseSarasSeedProvider", CbseSarasSeedProvider()),
                ("BingHTMLProvider", BingHTMLProvider()),
                ("DuckDuckGoHTMLProvider", DuckDuckGoHTMLProvider()),
                ("PublicDirectoryProvider", PublicDirectoryProvider())
            ]

        task.progress = 10
        db.commit()

        active_leads: List[Dict[str, Any]] = []

        for prov_name, provider in providers:
            if len(active_leads) >= target_min:
                break

            log_event(db, task.id, "[DISCOVERY START]", f"[DISCOVERY START] provider=\"{prov_name}\" query=\"{task.keyword} in {task.location}\"")
            prov_start = time.time()

            try:
                prov_candidates = await provider.discover(
                    location=task.location,
                    keyword=task.keyword,
                    max_results=task.max_results,
                    client=shared_client
                )

                for c in prov_candidates:
                    if len(active_leads) >= target_min:
                        break

                    name_raw = c["name"]
                    url_raw = c.get("possible_website") or ""

                    name_low = name_raw.lower().strip()
                    url_low = url_raw.lower().strip()

                    if name_low in seen_names or (url_low and url_low in seen_urls):
                        continue

                    # -------------------------------------------------------------
                    # STAGE 1: REAL ORGANIZATION IDENTITY VERIFICATION
                    # -------------------------------------------------------------
                    is_real_org, id_reason, id_meta = verify_organization_identity(name_raw, url_raw, c.get("snippet", ""))
                    if not is_real_org:
                        rejection_metrics["not_an_organization"] += 1
                        log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Identity Filter: {id_reason}\"")
                        continue

                    # -------------------------------------------------------------
                    # STAGE 2: CATEGORY VERIFICATION
                    # -------------------------------------------------------------
                    is_cat_valid, cat_reason = verify_category_match(task.keyword, name_raw, c.get("category", ""), url_raw)
                    if not is_cat_valid:
                        rejection_metrics["category_mismatch"] += 1
                        log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Category Filter: {cat_reason}\"")
                        continue

                    # -------------------------------------------------------------
                    # STAGE 3: LOCATION VERIFICATION (Country, State/UT, District)
                    # -------------------------------------------------------------
                    is_loc_valid, loc_reason, loc_meta = verify_organization_location(
                        target_location_str=task.location,
                        org_name=name_raw,
                        detected_address=c.get("address", ""),
                        domain=url_raw
                    )
                    if not is_loc_valid and prov_name != "CbseSarasSeedProvider":
                        rejection_metrics["location_mismatch"] += 1
                        log_event(db, task.id, "[LOCATION REJECT]", f"[LOCATION REJECT] candidate=\"{name_raw}\" reason=\"Location Filter: {loc_reason}\"")
                        continue

                    seen_names.add(name_low)
                    if url_low:
                        seen_urls.add(url_low)

                    candidates.append(c)
                    task.discovered_count = len(candidates)
                    db.commit()

                    # -------------------------------------------------------------
                    # STAGE 4: OFFICIAL WEBSITE DISCOVERY & OWNERSHIP
                    # -------------------------------------------------------------
                    official_url = None
                    domain = None
                    res_err = None

                    async with RESOLUTION_SEMAPHORE:
                        official_url, domain, res_err = await resolve_official_website(
                            name_raw, task.location, url_raw, shared_client
                        )

                    if not official_url or not domain or is_directory_domain(domain):
                        rejection_metrics["directory_url"] += 1
                        log_event(
                            db, task.id, "[CANDIDATE REJECT]",
                            f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Official website unresolved or belongs to directory ({res_err or 'Unresolved domain'})\""
                        )
                        continue

                    has_dns = await check_dns_resolution(domain, timeout=4.0)
                    if not has_dns:
                        rejection_metrics["dns_failed"] += 1
                        log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" domain=\"{domain}\" reason=\"DNS resolution failed\"")
                        continue

                    # -------------------------------------------------------------
                    # STAGE 5: CRAWL VERIFIED OFFICIAL WEBSITE
                    # -------------------------------------------------------------
                    crawl_res = None
                    website_status = "ACTIVE"
                    website_reason = None

                    if domain in domain_crawl_cache:
                        crawl_res = domain_crawl_cache[domain]
                        website_status = crawl_res.get("status", "ACTIVE")
                        website_reason = crawl_res.get("reason")
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
                                c_dur = time.time() - c_start
                                total_http_time += c_dur
                                domain_crawl_cache[domain] = crawl_res
                                website_status = crawl_res.get("status", "ACTIVE")
                                website_reason = crawl_res.get("reason")
                            except Exception as crawl_err:
                                website_status = "FAILED"
                                website_reason = str(crawl_err)

                    if website_status not in ("SUCCESS", "ACTIVE") or not crawl_res:
                        rejection_metrics["unreachable"] += 1
                        log_event(db, task.id, "[CANDIDATE REJECT]", f"[CANDIDATE REJECT] candidate=\"{name_raw}\" reason=\"Official website unreachable or crawl failed ({website_reason or 'Crawl failed'})\":")
                        continue

                    # -------------------------------------------------------------
                    # STAGE 6: OFFICIAL WEBSITE LOCATION VERIFICATION
                    # -------------------------------------------------------------
                    address_str, city_str, state_str, pin_str = "", "", "", ""
                    emails_list = crawl_res["emails"] if crawl_res else []
                    phones_list = crawl_res["phones"] if crawl_res else []
                    socials_list = crawl_res["socials"] if crawl_res else []
                    people_list = crawl_res["people"] if crawl_res else []

                    if crawl_res and crawl_res.get("addresses"):
                        addr = crawl_res["addresses"][0]
                        address_str = addr.get("address") or ""
                        city_str = addr.get("city") or ""
                        state_str = addr.get("state") or ""
                        pin_str = addr.get("pincode") or ""

                    html_evidence = (crawl_res.get("page_title") or "") + " " + " ".join(crawl_res.get("headings") or [])
                    is_web_loc_valid, web_loc_reason, _ = verify_organization_location(
                        target_location_str=task.location,
                        org_name=name_raw,
                        detected_address=address_str,
                        html_text=html_evidence,
                        domain=domain or ""
                    )

                    if not is_web_loc_valid:
                        rejection_metrics["location_mismatch"] += 1
                        log_event(db, task.id, "[LOCATION REJECT]", f"[LOCATION REJECT] candidate=\"{name_raw}\" website address mismatch reason=\"{web_loc_reason}\"")
                        continue

                    # Seed contacts fallback if available
                    if c.get("pincode") and not pin_str: pin_str = c["pincode"]

                    # -------------------------------------------------------------
                    # STAGE 7: QUALITY SCORE & DEDUPLICATION
                    # -------------------------------------------------------------
                    target_loc_obj = normalize_target_location(task.location)

                    lead_res = {
                        "name": name_raw,
                        "category": task.keyword,
                        "address": address_str,
                        "city": city_str or target_loc_obj["target_city"],
                        "state": state_str or target_loc_obj["target_state_or_ut"],
                        "country": target_loc_obj["target_country"],
                        "pincode": pin_str,
                        "domain": domain,
                        "official_website_url": official_url,
                        "possible_website": official_url,
                        "website_status": website_status,
                        "website_reason": website_reason,
                        "source_url": c.get("source_url") or url_raw,
                        "discovery_source": c.get("discovery_source", "SEARCH_PROVIDER"),
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
                        "official_website_verified": True,
                        "confidence": "HIGH"
                    }

                    lead_res["confidence"] = calculate_lead_confidence(lead_res)

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
                        log_event(db, task.id, "[LEAD VERIFIED]", f"[LEAD VERIFIED] ({len(active_leads)}/{target_min}) org=\"{name_raw}\" domain=\"{domain}\"")

                    prog = min(10 + int((len(active_leads) / target_min) * 75), 85)
                    task.progress = prog
                    db.commit()

            except Exception as pe:
                log_event(db, task.id, "PROVIDER_BLOCKED", f"[PROVIDER] {prov_name} error/blocked: {pe}")

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

            if existing_org:
                updated_orgs_count += 1
                existing_org.task_id = task.id
                existing_org.updated_at = datetime.datetime.utcnow()
                existing_org.official_website_url = lead["official_website_url"]
                existing_org.identity_verified = True
                existing_org.category_verified = True
                existing_org.country_verified = True
                existing_org.state_verified = True
                existing_org.district_verified = True
                existing_org.location_verified = True
                existing_org.official_website_verified = True
                existing_org.confidence = lead["confidence"]
                org = existing_org
            else:
                new_orgs_count += 1
                org = Organization(
                    task_id=task.id,
                    district_id=dist_id,
                    name=lead["name"],
                    category=lead["category"],
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
                    official_website_verified=True,
                    confidence=lead["confidence"]
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
                        official_website_verified=True
                    )
                    db.add(tl)
                seen_task_lead_org_ids.add(org.id)

            web_url = lead.get("official_website_url")
            web_domain = lead.get("domain")
            existing_web = db.query(Website).filter(Website.organization_id == org.id).first()
            
            if existing_web:
                if web_domain: existing_web.domain = web_domain
                if web_url: existing_web.url = web_url
                existing_web.status = lead.get("website_status", "ACTIVE")
                existing_web.reason = lead.get("website_reason")
                web = existing_web
            else:
                web = Website(
                    organization_id=org.id,
                    domain=web_domain,
                    url=web_url,
                    status=lead.get("website_status", "ACTIVE"),
                    reason=lead.get("website_reason"),
                    discovery_source=lead["discovery_source"],
                    confidence=lead["confidence"]
                )
                db.add(web)
                db.flush()

            pages_map: Dict[str, SourcePage] = {}

            existing_emails = {e.email for e in org.email_addresses} if org.email_addresses else set()
            for e in lead["emails"]:
                if e["email"] not in existing_emails:
                    s_url = e["source_url"]
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
