import urllib.parse
import base64
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from app.core.config import settings
from app.services.scraper.base import DiscoveryProvider
from app.core.cbse_seed_data import TAMIL_NADU_CBSE_SCHOOLS, PUDUCHERRY_CBSE_SCHOOLS

from app.services.scraper.identification import is_generic_listing_page, is_directory_domain, extract_domain

class DiscoveryError(Exception):
    pass

class SearchProviderBlockedError(DiscoveryError):
    pass

def is_generic_listing_title(name: str, url: str = "") -> bool:
    is_gen, _ = is_generic_listing_page(name, url)
    return is_gen

def generate_multi_queries(keyword: str, location: str) -> List[str]:
    cat = keyword.strip()
    loc = location.strip()
    cat_plural = cat if cat.endswith("s") else f"{cat}s"
    cat_lower = cat.lower()

    # Location aliases (e.g. Puducherry <-> Pondicherry)
    loc_aliases = [loc]
    loc_low = loc.lower()
    if loc_low in ("puducherry", "pondicherry", "pondy"):
        loc_aliases = ["Puducherry", "Pondicherry"]
    elif loc_low in ("kanyakumari", "nagercoil"):
        loc_aliases = ["Kanyakumari", "Nagercoil"]
    elif loc_low in ("tiruchirappalli", "trichy"):
        loc_aliases = ["Tiruchirappalli", "Trichy"]

    queries = []
    for l in loc_aliases:
        queries.extend([
            f"{cat_plural} in {l} India",
            f"{cat} {l} official website",
            f"{cat_plural} {l} contact phone email",
            f"{cat} {l} address phone",
            f"best {cat_plural} in {l}",
            f"list of {cat_plural} in {l}"
        ])
        if "cbse" in cat_lower:
            queries.extend([
                f"CBSE affiliated schools in {l}",
                f"site:cbse.gov.in {l} school",
                f"CBSE school {l} contact",
                f"CBSE school {l} address"
            ])
        elif "hospital" in cat_lower:
            queries.extend([
                f"hospitals in {l} contact number",
                f"multispeciality hospital in {l}",
                f"government hospital in {l}",
                f"private hospital in {l}",
                f"site:gov.in hospital {l}",
                f"site:nic.in hospital {l}"
            ])
        elif "hotel" in cat_lower:
            queries.extend([
                f"hotels in {l} official website",
                f"resorts in {l} contact"
            ])
        elif "software" in cat_lower or "it" in cat_lower:
            queries.extend([
                f"software companies in {l} contact",
                f"IT company in {l} official site"
            ])

    # Deduplicate queries while preserving order
    seen_q = set()
    unique_queries = []
    for q in queries:
        if q.lower() not in seen_q:
            seen_q.add(q.lower())
            unique_queries.append(q)

    return unique_queries


def unwrap_bing_url(url: str, cite_text: str = "") -> str:
    """
    Unwraps Bing redirect links like https://www.bing.com/ck/a?!&&p=...
    """
    if not url or "bing.com/ck/a" not in url:
        return url

    # Try extracting u= parameter containing base64 encoded URL
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if "u" in params and params["u"]:
            u_val = params["u"][0]
            if u_val.startswith("a1"):
                b64_str = u_val[2:]
                # Add padding if needed
                padded = b64_str + "=" * (-len(b64_str) % 4)
                try:
                    decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
                except Exception:
                    decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
                if decoded.startswith("http://") or decoded.startswith("https://"):
                    return decoded
    except Exception:
        pass

    # Fallback to cite text if available
    if cite_text:
        cleaned_cite = cite_text.strip().split(" ")[0].replace("https://", "").replace("http://", "").rstrip("/")
        if "." in cleaned_cite and not cleaned_cite.startswith("bing.com"):
            return f"https://{cleaned_cite}"

    return url

def unwrap_ddg_url(url: str) -> str:
    """
    Unwraps DuckDuckGo redirect links like /l/?uddg=...
    """
    if not url:
        return url
    if "/l/?" in url or "uddg=" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in params:
                return params["uddg"][0]
        except Exception:
            pass
    return url

DISCOVERY_SEMAPHORE = asyncio.Semaphore(5)

class CbseSarasSeedProvider(DiscoveryProvider):
    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        candidates = []
        loc_lower = location.lower().strip()
        key_lower = keyword.lower().strip()

        if loc_lower in ("pondy", "pondicherry"):
            loc_lower = "puducherry"

        all_schools = TAMIL_NADU_CBSE_SCHOOLS + PUDUCHERRY_CBSE_SCHOOLS

        for school in all_schools:
            if len(candidates) >= max_results:
                break

            school_state = school["state"].lower()
            school_district = school["district"].lower()
            school_location = school.get("location", "").lower()

            matches_location = (
                loc_lower in school_state or 
                school_state in loc_lower or
                loc_lower in school_district or
                school_district in loc_lower or
                loc_lower in school_location
            )

            matches_keyword = (
                "cbse" in key_lower or 
                "school" in key_lower or
                key_lower in school["name"].lower()
            )

            if matches_location and matches_keyword:
                candidates.append({
                    "name": school["name"],
                    "category": "CBSE School",
                    "location": f"{school['district']}, {school['state']}",
                    "possible_website": school["website"],
                    "source_url": school.get("saras_url", "https://saras.cbse.gov.in/"),
                    "discovery_source": "CBSE SARAS Registry",
                    "discovery_source_type": "OFFICIAL_REGISTRY",
                    "confidence": "HIGH",
                    "affiliation_no": school.get("affiliation_no", ""),
                    "pincode": school.get("pincode", "")
                })

        return candidates


class GovernmentDirectoryProvider(DiscoveryProvider):
    """
    Discovers candidate organizations from official government department pages,
    state portals, and district directories (.gov.in, .nic.in).
    """
    def __init__(self):
        self.headers = {
            "User-Agent": settings.SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        from app.services.scraper.identification import is_candidate_relevant, is_generic_listing_page

        candidates: List[Dict[str, Any]] = []
        seen_names: set = set()

        loc_low = location.lower().strip()
        cat_low = keyword.lower().strip()

        gov_queries = [
            f"site:gov.in {keyword} {location}",
            f"site:nic.in {keyword} {location}",
            f"government department {keyword} {location}",
            f"official directory {keyword} {location} gov.in"
        ]

        if "puducherry" in loc_low or "pondicherry" in loc_low:
            if "hospital" in cat_low:
                gov_queries.extend([
                    "site:health.py.gov.in hospital",
                    "site:py.gov.in hospital",
                    "site:puducherry-dt.gov.in hospital",
                    "Puducherry government hospital list"
                ])
            elif "school" in cat_low:
                gov_queries.extend([
                    "site:schooledn.py.gov.in school",
                    "site:py.gov.in school"
                ])
        elif "erode" in loc_low or "tamil" in loc_low or "chennai" in loc_low or "salem" in loc_low or "coimbatore" in loc_low:
            if "hospital" in cat_low:
                gov_queries.extend([
                    f"site:tn.gov.in hospital {location}",
                    f"site:tnhealth.tn.gov.in hospital {location}"
                ])
            elif "school" in cat_low:
                gov_queries.extend([
                    f"site:tnschools.gov.in school {location}",
                    f"site:tn.gov.in school {location}"
                ])

        own_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False)
            own_client = True

        try:
            async def fetch_gov_query(q: str) -> List[Dict[str, Any]]:
                async with DISCOVERY_SEMAPHORE:
                    q_candidates = []
                    encoded_query = urllib.parse.quote_plus(q)
                    url = f"https://www.bing.com/search?q={encoded_query}"
                    try:
                        resp = await client.get(url, headers=self.headers)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "lxml")
                            results = soup.find_all("li", class_="b_algo")
                            if results:
                                for item in results:
                                    h2 = item.find("h2")
                                    if not h2 or not h2.find("a"):
                                        continue
                                    a_tag = h2.find("a")
                                    raw_link = a_tag["href"]
                                    cite_elem = item.find("cite")
                                    cite_text = cite_elem.get_text(strip=True) if cite_elem else ""
                                    actual_url = unwrap_bing_url(raw_link, cite_text)
                                    title = a_tag.get_text(strip=True)
                                    org_name = title.split(" - ")[0].split(" | ")[0].split(" : ")[0].strip()

                                    is_gen, _ = is_generic_listing_page(org_name, actual_url)
                                    if is_gen:
                                        continue

                                    is_rel, _ = is_candidate_relevant(org_name, keyword, location, actual_url)
                                    if is_rel:
                                        n_low = org_name.lower()
                                        if n_low not in seen_names:
                                            seen_names.add(n_low)
                                            q_candidates.append({
                                                "name": org_name,
                                                "category": keyword,
                                                "location": location,
                                                "possible_website": actual_url if not any(g in actual_url for g in ["bing.com", "gov.in", "nic.in"]) else None,
                                                "source_url": actual_url,
                                                "discovery_source": f"Government Directory ({extract_domain(actual_url) or 'gov.in'})",
                                                "discovery_source_type": "GOVERNMENT_DIRECTORY",
                                                "confidence": "HIGH"
                                            })
                            else:
                                headings = soup.find_all(["h2", "h3", "h4"])
                                for h in headings:
                                    org_name = h.get_text(strip=True)
                                    if len(org_name) < 5 or any(k in org_name.lower() for k in ["health department", "hospitals in", "directory", "welcome"]):
                                        continue
                                    parent_text = h.parent.get_text(" ", strip=True) if h.parent else ""
                                    a_tag = h.find("a") or (h.parent.find("a") if h.parent else None)
                                    actual_url = a_tag["href"] if (a_tag and a_tag.has_attr("href")) else "https://gov.in"
                                    
                                    is_rel, _ = is_candidate_relevant(org_name, keyword, location, actual_url)
                                    if is_rel:
                                        n_low = org_name.lower()
                                        if n_low not in seen_names:
                                            seen_names.add(n_low)
                                            q_candidates.append({
                                                "name": org_name,
                                                "category": keyword,
                                                "location": location,
                                                "address": parent_text[:200] if parent_text else "",
                                                "possible_website": actual_url if not any(g in actual_url for g in ["gov.in", "nic.in"]) else None,
                                                "source_url": url,
                                                "discovery_source": "Government Directory",
                                                "discovery_source_type": "GOVERNMENT_DIRECTORY",
                                                "confidence": "HIGH"
                                            })
                    except Exception as e:
                        print(f"[GOVT DISCOVERY] Query '{q}' error: {e}")
                    return q_candidates

            tasks = [fetch_gov_query(q) for q in gov_queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    for c in res:
                        candidates.append(c)
                        if len(candidates) >= max_results:
                            break
        finally:
            if own_client:
                await client.aclose()

        return candidates


class ExistingMasterProvider(DiscoveryProvider):
    """
    Discovers candidate organizations from pre-existing Master Organizations database records.
    """
    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        from app.core.database import SessionLocal
        from app.models.models import Organization
        from app.services.scraper.identification import normalize_category_and_subcategory
        from app.services.location_service import normalize_target_location

        candidates = []
        norm_cat, norm_subcat = normalize_category_and_subcategory(keyword)
        loc_obj = normalize_target_location(location)
        target_dist = loc_obj.get("target_district") or location.strip()

        db = SessionLocal()
        try:
            query = db.query(Organization).filter(Organization.category == norm_cat)
            if target_dist:
                query = query.filter(Organization.district.ilike(f"%{target_dist}%"))

            orgs = query.limit(max_results).all()
            for org in orgs:
                candidates.append({
                    "name": org.name,
                    "category": org.category,
                    "sub_category": org.sub_category,
                    "location": f"{org.district}, {org.state}",
                    "possible_website": org.official_website_url,
                    "source_url": org.official_website_url or "Master Organizations Index",
                    "discovery_source": "Master Organization Index",
                    "discovery_source_type": "EXISTING_MASTER_DB",
                    "confidence": "HIGH"
                })
        except Exception as e:
            print(f"[MASTER DB DISCOVERY ERROR] {e}")
        finally:
            db.close()

        return candidates


class DuckDuckGoHTMLProvider(DiscoveryProvider):
    def __init__(self):
        self.headers = {
            "User-Agent": settings.SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        queries = generate_multi_queries(keyword, location)
        candidates: List[Dict[str, Any]] = []
        seen_names: set = set()
        seen_urls: set = set()

        own_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False)
            own_client = True

        try:
            async def fetch_query(query: str) -> List[Dict[str, Any]]:
                async with DISCOVERY_SEMAPHORE:
                    q_candidates = []
                    encoded_query = urllib.parse.quote_plus(query)
                    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                    try:
                        response = await asyncio.wait_for(client.get(url, headers=self.headers), timeout=4.0)
                        if response.status_code != 200:
                            return q_candidates

                        soup = BeautifulSoup(response.text, "lxml")
                        result_bodies = soup.find_all("div", class_="result__body")

                        for body in result_bodies:
                            title_elem = body.find("a", class_="result__a")
                            if not title_elem or not title_elem.get("href"):
                                continue

                            raw_href = title_elem["href"]
                            actual_url = unwrap_ddg_url(raw_href)

                            title_text = title_elem.get_text(strip=True)
                            org_name = title_text.split(" - ")[0].split(" | ")[0].split(" : ")[0].strip()

                            if is_generic_listing_title(org_name, actual_url):
                                continue

                            name_lower = org_name.lower()
                            if name_lower in seen_names or actual_url in seen_urls:
                                continue

                            possible_web = actual_url
                            if any(engine in actual_url.lower() for engine in ["duckduckgo.com", "google.com", "bing.com"]):
                                possible_web = ""

                            q_candidates.append({
                                "name": org_name,
                                "category": keyword,
                                "location": location,
                                "possible_website": possible_web,
                                "source_url": url,
                                "discovery_source": "DuckDuckGo",
                                "discovery_source_type": "SEARCH_ENGINE",
                                "confidence": "MEDIUM"
                            })
                    except Exception as e:
                        print(f"[DISCOVERY] DuckDuckGo query error '{query}': {e}")

                    return q_candidates

            tasks = [fetch_query(q) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, list):
                    for c in res:
                        n_low = c["name"].lower()
                        u_low = (c["possible_website"] or "").lower()
                        if n_low not in seen_names and (not u_low or u_low not in seen_urls):
                            seen_names.add(n_low)
                            if u_low:
                                seen_urls.add(u_low)
                            candidates.append(c)
                            if len(candidates) >= max_results:
                                break
        finally:
            if own_client:
                await client.aclose()

        return candidates


class BingHTMLProvider(DiscoveryProvider):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        queries = generate_multi_queries(keyword, location)
        candidates: List[Dict[str, Any]] = []
        seen_names: set = set()
        seen_urls: set = set()

        own_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False)
            own_client = True

        try:
            async def fetch_query(query: str) -> List[Dict[str, Any]]:
                async with DISCOVERY_SEMAPHORE:
                    q_candidates = []
                    encoded_query = urllib.parse.quote_plus(query)
                    url = f"https://www.bing.com/search?q={encoded_query}"
                    try:
                        response = await asyncio.wait_for(client.get(url, headers=self.headers), timeout=4.0)
                        if response.status_code != 200:
                            return q_candidates
                        soup = BeautifulSoup(response.text, "lxml")
                        results = soup.find_all("li", class_="b_algo")
                        for item in results:
                            h2 = item.find("h2")
                            if not h2:
                                continue
                            a_tag = h2.find("a")
                            if not a_tag or not a_tag.get("href"):
                                continue
                            raw_link = a_tag["href"]
                            cite_elem = item.find("cite")
                            cite_text = cite_elem.get_text(strip=True) if cite_elem else ""

                            link = unwrap_bing_url(raw_link, cite_text)

                            title = a_tag.get_text(strip=True)
                            org_name = title.split(" - ")[0].split(" | ")[0].split(" : ")[0].strip()

                            from app.services.scraper.identification import is_candidate_relevant
                            is_rel, _ = is_candidate_relevant(org_name, keyword, location, link)
                            if not is_rel:
                                continue

                            name_lower = org_name.lower()
                            if name_lower in seen_names or link in seen_urls:
                                continue

                            possible_web = link
                            if any(engine in link.lower() for engine in ["bing.com", "google.com", "duckduckgo.com"]):
                                possible_web = ""

                            q_candidates.append({
                                "name": org_name,
                                "category": keyword,
                                "location": location,
                                "possible_website": possible_web,
                                "source_url": url,
                                "discovery_source": "Bing Search",
                                "discovery_source_type": "SEARCH_ENGINE",
                                "confidence": "MEDIUM"
                            })
                    except Exception as e:
                        print(f"[DISCOVERY] Bing query error '{query}': {e}")
                    return q_candidates

            tasks = [fetch_query(q) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, list):
                    for c in res:
                        n_low = c["name"].lower()
                        u_low = (c["possible_website"] or "").lower()
                        if n_low not in seen_names and (not u_low or u_low not in seen_urls):
                            seen_names.add(n_low)
                            if u_low:
                                seen_urls.add(u_low)
                            candidates.append(c)
                            if len(candidates) >= max_results:
                                break
        finally:
            if own_client:
                await client.aclose()

        return candidates


class PublicDirectoryProvider(DiscoveryProvider):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        from app.services.scraper.identification import is_candidate_relevant

        candidates: List[Dict[str, Any]] = []
        seen_names: set = set()

        loc_low = location.lower().strip().replace(" ", "-")
        cat_low = keyword.lower().strip().replace(" ", "-")

        directory_page_urls = [
            f"https://www.justdial.com/{loc_low}/{cat_low}s",
            f"https://www.sulekha.com/{cat_low}s/{loc_low}",
            f"https://www.indialocals.com/{loc_low}/{cat_low}",
        ]

        if "school" in cat_low:
            directory_page_urls.extend([
                f"https://educonnectin.com/schools-by-district/tamil-nadu/{loc_low}",
                f"https://educonnectin.com/schools/tamil-nadu/{loc_low}",
                f"https://targetstudy.com/school/schools-in-{loc_low}.html",
                f"https://www.schoolmykids.com/schools/india/list-of-schools-in-{loc_low}",
                f"https://school.careers360.com/schools/schools-in-{loc_low}",
            ])
        elif "college" in cat_low or "university" in cat_low:
            directory_page_urls.extend([
                f"https://targetstudy.com/colleges/colleges-in-{loc_low}.html",
                f"https://collegedunia.com/{loc_low}-colleges",
                f"https://www.shiksha.com/colleges/{loc_low}",
                f"https://www.careerindia.com/colleges/colleges-in-{loc_low}/",
            ])
        elif "hotel" in cat_low or "resort" in cat_low:
            directory_page_urls.extend([
                f"https://www.tripadvisor.in/Hotels-g-{loc_low}-Hotels.html",
                f"https://www.goibibo.com/hotels/hotels-in-{loc_low}-ct/",
            ])
        elif "hospital" in cat_low or "clinic" in cat_low:
            directory_page_urls.extend([
                f"https://www.vaidam.com/hospitals/{loc_low}",
                f"https://www.credihealth.com/hospitals/{loc_low}",
            ])

        own_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False)
            own_client = True

        try:
            async def parse_dir_url(dir_url: str) -> List[Dict[str, Any]]:
                async with DISCOVERY_SEMAPHORE:
                    dir_candidates = []
                    try:
                        d_resp = await asyncio.wait_for(client.get(dir_url, headers=self.headers), timeout=4.0)
                        if d_resp.status_code == 200:
                            d_soup = BeautifulSoup(d_resp.text, "lxml")
                            for tag in d_soup.find_all(["a", "h2", "h3", "h4"]):
                                text = tag.get_text(strip=True)
                                href = tag.get("href", "") if tag.name == "a" else ""
                                if not href:
                                    a_tag = tag.find_parent("a") or tag.find("a")
                                    if a_tag:
                                        href = a_tag.get("href", "")

                                full_link = urllib.parse.urljoin(dir_url, href) if href else dir_url
                                if len(text) >= 6:
                                    text_clean = text.split(" - ")[0].split(" | ")[0].strip()
                                    is_rel, _ = is_candidate_relevant(text_clean, keyword, location, full_link)
                                    if is_rel and len(text_clean) >= 6:
                                        n_low = text_clean.lower().strip()
                                        if n_low not in seen_names:
                                            seen_names.add(n_low)
                                            dir_candidates.append({
                                                "name": text_clean,
                                                "category": keyword,
                                                "location": location,
                                                "possible_website": full_link if full_link and not is_directory_domain(full_link) else None,
                                                "source_url": full_link,
                                                "discovery_source": f"Directory Page ({extract_domain(dir_url)})",
                                                "discovery_source_type": "PUBLIC_DIRECTORY",
                                                "confidence": "MEDIUM"
                                            })
                    except Exception:
                        pass
                    return dir_candidates

            tasks = [parse_dir_url(u) for u in directory_page_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, list):
                    for c in res:
                        candidates.append(c)
                        if len(candidates) >= max_results:
                            break
        finally:
            if own_client:
                await client.aclose()

        return candidates


class UserURLProvider(DiscoveryProvider):
    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        urls = [url.strip() for url in location.split(",") if url.strip()]
        candidates = []
        for url in urls:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            name = domain.replace("www.", "").split(".")[0].capitalize()
            candidates.append({
                "name": f"{name} (User Provided)",
                "category": keyword or "Scraped Link",
                "location": "Direct URL",
                "possible_website": url,
                "source_url": url,
                "discovery_source": "User Provided Direct URL",
                "discovery_source_type": "USER_URL",
                "confidence": "HIGH"
            })
        return candidates


class MultiSourceDiscoveryManager:
    """
    Coordinator executing multi-provider parallel candidate discovery across
    Government Directories, Official Registries, Search Engines, Master DB, and Public Directories.
    Enforces per-provider timeouts so one failing provider never blocks the entire task.
    """
    def __init__(self, custom_providers: Optional[List[DiscoveryProvider]] = None):
        if custom_providers is not None:
            self.providers = [(getattr(p, "provider_name", p.__class__.__name__), p) for p in custom_providers]
        else:
            self.providers = [
                ("ExistingMasterProvider", ExistingMasterProvider()),
                ("CbseSarasSeedProvider", CbseSarasSeedProvider()),
                ("GovernmentDirectoryProvider", GovernmentDirectoryProvider()),
                ("BingHTMLProvider", BingHTMLProvider()),
                ("DuckDuckGoHTMLProvider", DuckDuckGoHTMLProvider()),
                ("PublicDirectoryProvider", PublicDirectoryProvider())
            ]

    async def discover_candidates(
        self,
        location: str = "",
        keyword: str = "",
        max_results: int = 100,
        shared_client: Optional[httpx.AsyncClient] = None,
        db=None,
        category: str = ""
    ) -> List[Dict[str, Any]]:
        target_category = category or keyword
        target_location = location
        all_candidates: List[Dict[str, Any]] = []
        seen_names: set = set()
        seen_urls: set = set()

        async def run_single_provider(name: str, prov: DiscoveryProvider) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
            try:
                # Per-provider bounded timeout (8.0 seconds)
                results = await asyncio.wait_for(
                    prov.discover(location=target_location, keyword=target_category, max_results=max_results, client=shared_client),
                    timeout=8.0
                )
                return name, results or [], None
            except Exception as err:
                return name, [], str(err)

        tasks = [run_single_provider(p_name, p_obj) for p_name, p_obj in self.providers]
        prov_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in prov_results:
            if isinstance(res, tuple):
                p_name, cand_list, p_err = res
                if p_err:
                    print(f"[PROVIDER FAILURE] Provider '{p_name}' failed/timed out: {p_err}. Continuing with other providers.")
                for c in cand_list:
                    name_raw = (c.get("name") or "").strip()
                    url_raw = (c.get("possible_website") or "").strip()
                    name_low = name_raw.lower()
                    url_low = url_raw.lower()

                    if name_raw and name_low not in seen_names:
                        if not url_low or url_low not in seen_urls:
                            seen_names.add(name_low)
                            if url_low:
                                seen_urls.add(url_low)
                            all_candidates.append(c)

        return all_candidates
