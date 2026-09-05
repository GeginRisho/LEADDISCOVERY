import urllib.parse
import base64
import asyncio
from typing import List, Dict, Any, Optional
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

def generate_multi_queries(location: str, category: str) -> List[str]:
    loc = location.strip()
    cat = category.strip()
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
                f"multispeciality hospital in {l}"
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
                    "discovery_source": "SEEDED_OFFICIAL_DIRECTORY",
                    "confidence": "HIGH",
                    "affiliation_no": school.get("affiliation_no", ""),
                    "pincode": school.get("pincode", "")
                })

        return candidates

# is_generic_listing_title is imported/delegated to app.services.scraper.identification.is_generic_listing_page

DISCOVERY_SEMAPHORE = asyncio.Semaphore(5)

class DuckDuckGoHTMLProvider(DiscoveryProvider):
    def __init__(self):
        self.headers = {
            "User-Agent": settings.SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
        queries = generate_multi_queries(location, keyword)
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
                        response = await asyncio.wait_for(client.get(url, headers=self.headers), timeout=3.0)
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
        queries = generate_multi_queries(location, keyword)
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
                        response = await client.get(url, headers=self.headers)
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
                        d_resp = await client.get(dir_url, headers=self.headers)
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
    async def discover(self, location: str, keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
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
                "discovery_source": "User URL",
                "confidence": "HIGH"
            })
        return candidates

