import asyncio
import socket
import urllib.parse
import re
from typing import Dict, Any, Tuple, Optional
import httpx
from app.services.scraper.robots import is_safe_url
from app.services.scraper.identification import clean_org_name, extract_domain, is_directory_domain
from app.services.location_service import verify_organization_location

async def check_dns_resolution(domain: str, timeout: float = 5.0) -> bool:
    if not domain:
        return False
    try:
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.getaddrinfo(domain, 80, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM),
            timeout=timeout
        )
        return True
    except Exception:
        return False

def is_location_matching(
    requested_location: str,
    org_name: str,
    detected_address: str = "",
    html_text: str = "",
    domain: str = ""
) -> Tuple[bool, str]:
    """
    Delegates to Location Matching Engine in location_service.py
    """
    is_valid, reason, _ = verify_organization_location(
        target_location_str=requested_location,
        org_name=org_name,
        detected_address=detected_address,
        html_text=html_text,
        domain=domain
    )
    return is_valid, reason

def calculate_lead_confidence(lead: Dict[str, Any]) -> str:
    """
    Computes quality confidence score: HIGH, MEDIUM, LOW.
    HIGH confidence requires ALL verification flags to be TRUE:
    - identity_verified == True
    - category_verified == True
    - country_verified == True
    - state_verified == True
    - district_verified == True
    - location_verified == True
    - official_website_verified == True
    """
    id_ver = lead.get("identity_verified", True)
    cat_ver = lead.get("category_verified", True)
    coun_ver = lead.get("country_verified", True)
    state_ver = lead.get("state_verified", True)
    dist_ver = lead.get("district_verified", True)
    loc_ver = lead.get("location_verified", True)
    web_ver = lead.get("official_website_verified", True)

    domain = lead.get("domain")
    has_web = bool(domain and not is_directory_domain(domain))

    # All core flags must be True for HIGH confidence
    all_flags_true = (id_ver and cat_ver and coun_ver and state_ver and dist_ver and loc_ver and web_ver and has_web)

    if all_flags_true and (lead.get("emails") or lead.get("phones") or lead.get("address")):
        return "HIGH"

    if id_ver and cat_ver and loc_ver and (has_web or lead.get("phones") or lead.get("emails")):
        return "MEDIUM"

    return "LOW"
