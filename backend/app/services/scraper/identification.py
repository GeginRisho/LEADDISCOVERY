import urllib.parse
import re
from typing import Dict, Any, Tuple, Optional, List
from app.services.scraper.identity_verification import verify_organization_identity
from app.services.location_service import verify_organization_location

# Generic Directory / Aggregator Domain Blacklist (Discovery Protection)
DIRECTORY_DOMAINS = {
    # Search engines
    "google.com", "google.co.in", "bing.com", "duckduckgo.com", "yahoo.com", "baidu.com", "yandex.com",
    # Travel Guides, Encyclopedias & General Reference
    "wikivoyage.org", "wikipedia.org", "wiktionary.org", "britannica.com", "wikitravel.org",
    # Directories & Aggregators
    "justdial.com", "sulekha.com", "indiamart.com", "tradeindia.com", "exportersindia.com", "tripadvisor.com",
    "tripadvisor.in", "booking.com", "makemytrip.com", "goibibo.com", "agoda.com", "yelp.com", "yellowpages.com",
    "yellowpages.in", "cityyellowpages.com", "asklaila.com", "quikr.com", "olx.in", "easemytrip.com",
    "oyorooms.com", "treebo.com", "fabhotels.com", "findby.in", "indialocals.com", "yatra.com", "cleartrip.com",
    "expedia.com", "trivago.com", "hotels.com", "airbnb.com", "airbnb.co.in", "internshala.com", "shiksha.com",
    "schoolmykids.com", "collegedunia.com", "careers360.com", "collegesimply.com", "collegedekho.com",
    "univstats.com", "collegeevaluator.com", "targetstudy.com", "jagranjosh.com", "getmyuni.com", "vedantu.com",
    "byjus.com", "unacademy.com", "urbanpro.com", "mapsofindia.com", "dialindia.com", "enrollmychild.com",
    "schoolspedia.in", "edustoke.com", "admitbee.in", "educonnectin.com", "trustpilot.com", "g2.com", "capterra.com",
    "schoolsindia.net", "schools.org.in", "schooldekho.org", "schooldekho.in", "icbse.com", "vidyavision.com",
    "holidify.com", "thrillophilia.com", "traveloka.com", "nobroker.in", "magicbricks.com", "housing.com", "99acres.com",
    "zomato.com", "swiggy.com", "dineout.co.in", "eatsure.com", "bajajfinserv.in", "inspex.in", "quickcompany.in",
    "tatacliq.com", "flipkart.com", "myntra.com", "ajio.com", "nykaa.com", "snapdeal.com",
    # Healthcare & Medical Tourism Aggregators
    "vaidam.com", "vaidam.in", "credihealth.com", "lybrate.com", "practo.com", "medindia.net", "docprime.com",
    "clinicspots.com", "medifee.com", "sehat.com", "liberate.in", "myupchar.com", "1mg.com", "pharmeasy.in",
    "apollo247.com", "netmeds.com",
    # Government & Board Central Portals (Not Individual Organizations)
    "cbse.gov.in", "saras.cbse.gov.in", "cbseit.in", "nic.in", "gov.in", "py.gov.in", "tn.gov.in", "kanniyakumari.nic.in",
    "cbseboard.org", "results.cbseboard.org", "cbseboard.in", "cbse.nic.in", "icbse.com", "cbseresults.nic.in",
    "tnresults.nic.in", "dge.tn.gov.in", "results.gov.in",
    # Social Platforms, Technical Vendors & Forums
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "pinterest.com", "tumblr.com",
    "reddit.com", "crunchbase.com", "glassdoor.com", "indeed.com", "medium.com", "wordpress.com", "blogspot.com",
    "scribd.com", "substack.com", "quora.com", "youtube.com", "microsoft.com", "apple.com", "weforum.org", "zhihu.com",
    "amazon.com", "amazon.in"
}

CATEGORY_PATH_PATTERNS = [
    "/public-utility-category/", "/category/", "/categories/", "/utility/",
    "/directory/", "/search/", "/listing/", "/listings/", "/find/", "/list/",
    "/hotels-g", "/colleges-in-", "/schools-in-", "/hospitals-in-", "/wiki/", "/wiki"
]

def clean_org_name(name: str) -> str:
    name_clean = name.lower()
    name_clean = re.sub(r'[^\w\s]', '', name_clean)
    words = name_clean.split()
    filter_words = {"school", "schools", "college", "colleges", "institute", "institutes", 
                    "university", "hospital", "hospitals", "hotel", "hotels", "restaurant", 
                    "restaurants", "ltd", "limited", "pvt", "private", "co", "company", "and", "the"}
    filtered = [w for w in words if w not in filter_words]
    return " ".join(filtered) if filtered else name_clean

def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    
    try:
        parsed = urllib.parse.urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.count("/") == 2:
            normalized += "/"
        return normalized
    except Exception:
        return url

def extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        domain = domain.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def is_directory_domain(url_or_domain: str) -> bool:
    if not url_or_domain:
        return False
    domain = extract_domain(url_or_domain) if ("/" in url_or_domain or ":" in url_or_domain) else url_or_domain.lower().strip()
    if not domain:
        return False
    if domain.startswith("www."):
        domain = domain[4:]
    for blacklisted in DIRECTORY_DOMAINS:
        if domain == blacklisted or domain.endswith("." + blacklisted):
            return True
    return False

def is_generic_listing_page(name: str, url: str = "") -> Tuple[bool, str]:
    """
    Evaluates candidate name and URL using the generic identity verification engine.
    """
    is_real, reason, meta = verify_organization_identity(name, url)
    if not is_real:
        return True, f"Generic Page Filter: {reason} ({meta.get('entity_type')})"
    return False, "PASS"

def normalize_category_and_subcategory(category_str: str) -> Tuple[str, str]:
    """
    Normalizes user-specified category string into generic (category, sub_category).
    Examples:
      'CBSE school' -> ('SCHOOL', 'CBSE')
      'Matriculation school' -> ('SCHOOL', 'MATRICULATION')
      'International school' -> ('SCHOOL', 'INTERNATIONAL')
      'school' -> ('SCHOOL', 'SCHOOL')
      'Engineering college' -> ('COLLEGE', 'ENGINEERING')
      'Arts and science college' -> ('COLLEGE', 'ARTS_SCIENCE')
      'college' -> ('COLLEGE', 'COLLEGE')
      'Multispecialty hospital' -> ('HOSPITAL', 'MULTISPECIALTY')
      'hospital' -> ('HOSPITAL', 'HOSPITAL')
      'hotel' -> ('HOTEL', 'HOTEL')
      'Software company' -> ('SOFTWARE_COMPANY', 'SOFTWARE_COMPANY')
    """
    if not category_str:
        return "OTHER", "OTHER"

    cat_low = category_str.lower().strip()

    # Schools
    if "cbse" in cat_low and "school" in cat_low:
        return "SCHOOL", "CBSE"
    elif "matriculation" in cat_low or "matric" in cat_low:
        return "SCHOOL", "MATRICULATION"
    elif "international" in cat_low and "school" in cat_low:
        return "SCHOOL", "INTERNATIONAL"
    elif "school" in cat_low or "schools" in cat_low:
        return "SCHOOL", "SCHOOL"

    # Colleges
    if "engineering" in cat_low:
        return "COLLEGE", "ENGINEERING"
    elif "arts" in cat_low or "science" in cat_low:
        return "COLLEGE", "ARTS_SCIENCE"
    elif "college" in cat_low or "colleges" in cat_low or "university" in cat_low:
        return "COLLEGE", "COLLEGE"

    # Hospitals
    if "multispecialty" in cat_low or "multi specialty" in cat_low:
        return "HOSPITAL", "MULTISPECIALTY"
    elif "hospital" in cat_low or "hospitals" in cat_low or "clinic" in cat_low:
        return "HOSPITAL", "HOSPITAL"

    # Hotels
    if "hotel" in cat_low or "hotels" in cat_low or "resort" in cat_low:
        return "HOTEL", "HOTEL"

    # Software / IT Companies
    if "software" in cat_low or "it company" in cat_low or "tech" in cat_low:
        return "SOFTWARE_COMPANY", "SOFTWARE_COMPANY"

    clean_tok = re.sub(r'[^a-zA-Z0-9]', '_', cat_low).upper().strip('_')
    return clean_tok or "OTHER", clean_tok or "OTHER"


def verify_category_match(requested_category: str, candidate_name: str, candidate_category: str = "", candidate_url: str = "") -> Tuple[bool, str]:
    """
    Dynamically verifies whether candidate matches the user-requested organization category.
    Enforces strict category indicator matching and rejects cross-category conflicts.
    """
    req_low = requested_category.lower().strip()
    cand_low = candidate_name.lower().strip()
    url_low = (candidate_url or "").lower().strip()
    combined = f"{cand_low} {url_low} {(candidate_category or '').lower()}"

    req_cat, req_subcat = normalize_category_and_subcategory(requested_category)

    if req_cat == "SCHOOL":
        if any(conf in cand_low for conf in ["hospital", "hotel", "resort", "college", "university"]):
            return False, f"CATEGORY_MISMATCH (Candidate conflicts with school category)"
            
        if req_subcat == "CBSE":
            if any(bad in cand_low for bad in ["cbse result", "cbse exam", "cbse board", "cbse syllabus", "sample paper", "date sheet", "admit card"]):
                return False, "CATEGORY_MISMATCH (Exam/Board result page)"
            if not any(good in combined for good in ["school", "vidyalaya", "academy", "convent", "gurukul", "public school", "high school", "cbse"]):
                return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' does not indicate a school entity)"
            if "matriculation" in cand_low and "cbse" not in combined:
                return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' is a Matriculation school, not a CBSE school)"
        else:
            if not any(good in combined for good in ["school", "vidyalaya", "academy", "convent", "gurukul", "public school", "high school", "matriculation"]):
                return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' does not indicate a school entity)"

    elif req_cat == "HOTEL":
        if any(conf in cand_low for conf in ["school", "college", "university", "hospital", "software", "technologies", "electron"]):
            return False, f"CATEGORY_MISMATCH (Candidate conflicts with hotel category)"
        if not any(good in combined for good in ["hotel", "resort", "inn", "lodge", "lodging", "suites", "residency", "palace", "grand", "stay", "guest house", "homestay", "villa", "cottage", "spa", "hospitality"]):
            return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' does not indicate a hotel/lodging entity)"

    elif req_cat == "HOSPITAL":
        if any(conf in cand_low for conf in ["school", "college", "university", "hotel", "resort"]):
            return False, f"CATEGORY_MISMATCH (Candidate conflicts with hospital category)"
        if not any(good in combined for good in ["hospital", "clinic", "healthcare", "medical", "nursing home", "health center", "care", "eye center"]):
            return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' does not indicate a hospital/healthcare entity)"

    elif req_cat == "COLLEGE":
        if any(conf in cand_low for conf in ["hospital", "hotel", "resort", "school"]):
            return False, f"CATEGORY_MISMATCH (Candidate conflicts with college category)"
        if not any(good in combined for good in ["college", "university", "institute", "institution", "campus", "polytechnic", "vidyapeeth"]):
            return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' does not indicate a higher education college/university)"

    elif req_cat == "SOFTWARE_COMPANY":
        if any(conf in cand_low for conf in ["school", "college", "university", "hotel", "resort", "hospital"]):
            return False, f"CATEGORY_MISMATCH (Candidate conflicts with software/IT company category)"
        if not any(good in combined for good in ["software", "tech", "technologies", "it ", "it-", "solutions", "infotech", "systems", "digital", "labs", "data", "cyber", "cloud", "ai", "consulting"]):
            return False, f"CATEGORY_MISMATCH (Candidate '{candidate_name}' does not indicate an IT/software company)"

    elif req_cat == "COMPANY":
        if any(conf in cand_low for conf in ["school", "college", "university", "hotel", "resort", "hospital"]):
            return False, f"CATEGORY_MISMATCH (Candidate conflicts with company category)"

    return True, "PASS"

def is_candidate_relevant(name: str, keyword: str, location: str, url: str = "") -> Tuple[bool, str]:
    """
    Comprehensive multi-stage relevance check combining:
    1. Generic Identity Verification (Reject travel guides, articles, wikivoyage, exam portals)
    2. Dynamic Category Verification
    3. Generic Location Verification (Country, State/UT, District)
    """
    if not name or len(name.strip()) < 3:
        return False, "Candidate name is empty or too short (<3 chars)"

    # Stage 1: Identity Verification
    is_real, id_reason, meta = verify_organization_identity(name, url)
    if not is_real:
        return False, f"IDENTITY REJECT: Candidate is not a real organization ({id_reason})"

    # Stage 2: Category Verification
    cat_valid, cat_reason = verify_category_match(keyword, name, "", url)
    if not cat_valid:
        return False, f"CATEGORY REJECT: {cat_reason}"

    # Stage 3: Location Verification
    loc_valid, loc_reason, _ = verify_organization_location(
        target_location_str=location,
        org_name=name,
        detected_address=location,
        html_text=f"{name} {location}",
        domain=url
    )
    if not loc_valid:
        return False, f"LOCATION REJECT: {loc_reason}"

    return True, "PASS"

def identify_official_website(
    org_name: str, 
    possible_url: str,
    jsonld_types: Optional[List[str]] = None,
    html_text: str = ""
) -> Dict[str, Any]:
    """
    Multi-Signal Official Website Verification Engine.
    Determines whether a domain belongs to the organization using multiple signals:
    - Domain is NOT a directory/wikivoyage/board/aggregator portal
    - Domain brand token alignment OR institutional domain structure (.edu.in, .ac.in, .org)
    - Presence of Organization / LocalBusiness JSON-LD schema or Contact page structure
    
    Returns Dict with: is_official, is_directory_source, normalized_url, domain, confidence, reason.
    """
    if not possible_url:
        return {
            "is_official": False,
            "is_directory_source": False,
            "normalized_url": "",
            "domain": "",
            "confidence": "LOW",
            "reason": "No URL provided."
        }
        
    normalized = normalize_url(possible_url)
    domain = extract_domain(normalized)
    
    if not domain:
        return {
            "is_official": False,
            "is_directory_source": False,
            "normalized_url": normalized,
            "domain": "",
            "confidence": "LOW",
            "reason": "Could not parse domain from URL."
        }

    # Check if domain is a known non-organization portal (directory, wikivoyage, etc.)
    if is_directory_domain(domain):
        return {
            "is_official": False,
            "is_directory_source": True,
            "normalized_url": normalized,
            "domain": domain,
            "confidence": "LOW",
            "reason": f"URL belongs to search/discovery directory portal: {domain}"
        }

    path_lower = urllib.parse.urlparse(normalized).path.lower()
    for cat_pattern in CATEGORY_PATH_PATTERNS:
        if cat_pattern in path_lower:
            return {
                "is_official": False,
                "is_directory_source": True,
                "normalized_url": normalized,
                "domain": domain,
                "confidence": "LOW",
                "reason": f"URL path indicates category/wiki listing page: {path_lower}"
            }

    # Brand alignment and multi-signal score
    clean_org = clean_org_name(org_name)
    clean_domain = domain.split(".")[0]
    
    org_words = set(w for w in clean_org.split() if len(w) >= 3)
    domain_words = set(re.split(r'[^a-zA-Z0-9]', clean_domain))
    
    matches = org_words.intersection(domain_words)
    
    # Institutional top-level domains (.edu.in, .ac.in, .org.in, .edu, .ac)
    is_institutional = any(inst in domain for inst in [".edu.in", ".ac.in", ".org.in", ".edu", ".ac", ".school"])

    if len(matches) >= 1 or is_institutional or (jsonld_types and any(t.lower() in ["organization", "school", "localbusiness"] for t in jsonld_types)):
        return {
            "is_official": True,
            "is_directory_source": False,
            "normalized_url": normalized,
            "domain": domain,
            "confidence": "HIGH" if (len(matches) >= 2 or is_institutional) else "MEDIUM",
            "reason": f"Multi-signal official domain verified (Matches: {matches}, Institutional: {is_institutional})"
        }

    return {
        "is_official": True,
        "is_directory_source": False,
        "normalized_url": normalized,
        "domain": domain,
        "confidence": "MEDIUM",
        "reason": "Domain is standalone and not on non-organization blacklist."
    }
