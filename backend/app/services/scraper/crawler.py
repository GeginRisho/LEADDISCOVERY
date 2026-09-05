import asyncio
import urllib.parse
from typing import List, Dict, Any, Set, Tuple, Optional
import httpx
from bs4 import BeautifulSoup
from app.core.config import settings
from app.services.scraper.robots import RobotsCache, safe_request, is_safe_url
from app.services.scraper.identification import extract_domain, normalize_url
from app.services.scraper.extractor import (
    extract_emails, extract_phones, extract_social_links,
    extract_json_ld_address, extract_address_from_html, extract_contact_person
)

# Heuristic to detect if page content is heavily client-side rendered (SPA)
def is_html_insufficient(html: str) -> bool:
    try:
        soup = BeautifulSoup(html, "lxml")
        # Decompose styling and scripts to check visible text length
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(strip=True)
        
        # If there is very little static text, but we find signs of SPA mounting
        if len(text) < 800:
            html_lower = html.lower()
            spa_indicators = [
                'id="root"', 'id="app"', 'id="__next"', 'id="__nuxt"',
                'react-root', 'ng-version', 'vue-container', '<noscript>'
            ]
            if any(indicator in html_lower for indicator in spa_indicators):
                return True
        return False
    except Exception:
        return False

def get_link_priority(url: str) -> int:
    path = urllib.parse.urlparse(url).path.lower()
    # Prioritize contact-related pages
    priority_keywords = [
        "contact", "reach", "about", "admission", "management", 
        "principal", "faculty", "staff", "location", "branch"
    ]
    for idx, keyword in enumerate(priority_keywords):
        if keyword in path:
            return idx # Earlier in list = higher priority (value 0, 1, 2...)
    return 999 # General pages have low priority

# Global Playwright Concurrency Limiter (Max 2 browser instances across application)
PLAYWRIGHT_SEMAPHORE = asyncio.Semaphore(2)

class DomainCrawler:
    def __init__(
        self, 
        start_url: str, 
        max_pages: int = 5, 
        max_depth: int = 1,
        user_agent: str = "*",
        client: Optional[httpx.AsyncClient] = None
    ):
        self.start_url = normalize_url(start_url)
        self.domain = extract_domain(self.start_url)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.user_agent = user_agent
        self.client = client
        
        self.visited_urls: Set[str] = set()
        self.robots_cache = RobotsCache()
        
        # Playwright resources (allocated lazily and reused for this domain)
        self.playwright_instance = None
        self.playwright_browser = None
        self.playwright_context = None

    async def get_playwright_context(self) -> Any:
        if not self.playwright_browser:
            from playwright.async_api import async_playwright
            self.playwright_instance = await async_playwright().start()
            self.playwright_browser = await self.playwright_instance.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
            )
            self.playwright_context = await self.playwright_browser.new_context(
                user_agent=settings.SCRAPER_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
        return self.playwright_context

    async def close_playwright(self):
        try:
            if self.playwright_context:
                await self.playwright_context.close()
                self.playwright_context = None
            if self.playwright_browser:
                await self.playwright_browser.close()
                self.playwright_browser = None
            if self.playwright_instance:
                await self.playwright_instance.stop()
                self.playwright_instance = None
        except Exception as e:
            print(f"Error shutting down Playwright: {e}")

    async def fetch_page_html(self, url: str) -> Tuple[Optional[str], str]:
        if not await is_safe_url(url):
            return None, "SSRF_BLOCKED"
            
        headers = {"User-Agent": settings.SCRAPER_USER_AGENT}
        
        # LEVEL 1: Fast HTTP GET
        level1_err_reason = "UNKNOWN_FAILURE"
        try:
            if self.client is not None:
                response = await safe_request(self.client, "GET", url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=8.0, verify=False) as temp_client:
                    response = await safe_request(temp_client, "GET", url, headers=headers)
                    
            if response.status_code == 200:
                html_content = response.text
                
                if is_html_insufficient(html_content):
                    print(f"[CRAWLER] Level 1 HTML insufficient for {url}. Queuing Playwright fallback (Semaphore 2)...")
                    async with PLAYWRIGHT_SEMAPHORE:
                        playwright_html = await self.fetch_with_playwright(url)
                    if playwright_html:
                        return playwright_html, "playwright"
                        
                return html_content, "httpx"
            else:
                level1_err_reason = f"HTTP_{response.status_code}"
        except Exception as e:
            err_msg = str(e).lower()
            if "getaddrinfo" in err_msg or "name or service not known" in err_msg or "connecterror" in err_msg:
                level1_err_reason = "DNS_RESOLUTION_FAILED"
            elif "timeout" in err_msg:
                level1_err_reason = "CONNECTION_TIMEOUT"
            elif "ssl" in err_msg or "tls" in err_msg or "certificate" in err_msg:
                level1_err_reason = "TLS_ERROR"
            else:
                level1_err_reason = f"HTTPX_ERROR_{type(e).__name__}"

        # Level 1 failed, try Playwright fallback under Semaphore
        try:
            async with PLAYWRIGHT_SEMAPHORE:
                playwright_html = await self.fetch_with_playwright(url)
            if playwright_html:
                return playwright_html, "playwright"
        except Exception:
            return None, f"{level1_err_reason}_PLAYWRIGHT_FAILED"

        return None, level1_err_reason

    async def fetch_with_playwright(self, url: str) -> Optional[str]:
        try:
            context = await self.get_playwright_context()
            page = await context.new_page()
            try:
                await page.goto(
                    url, 
                    timeout=8000, 
                    wait_until="domcontentloaded"
                )
                await asyncio.sleep(1)
                content = await page.content()
                return content
            finally:
                await page.close()
        except Exception as e:
            print(f"[CRAWLER] Playwright failed to fetch {url}: {e}")
            return None

    async def crawl(self) -> Dict[str, Any]:
        """
        Crawl the website, extracting contact information.
        
        Returns:
            Dict containing merged contacts, address, name, website metadata.
        """
        queue: List[Tuple[str, int]] = [(self.start_url, 0)]
        
        emails: List[Dict[str, Any]] = []
        phones: List[Dict[str, Any]] = []
        socials: List[Dict[str, Any]] = []
        people: List[Dict[str, Any]] = []
        addresses: List[Dict[str, Any]] = []
        
        crawled_count = 0
        failed_count = 0
        primary_failure_reason = "NO_PAGES_ACCESSED"
        blocked_by_robots = False
        robots_allowed = await self.robots_cache.is_allowed(self.start_url, settings.SCRAPER_USER_AGENT, client=self.client)
        
        if not robots_allowed:
            blocked_by_robots = True
            await self.close_playwright()
            return {
                "status": "BLOCKED",
                "reason": "ROBOTS_BLOCKED",
                "emails": [], "phones": [], "socials": [], "people": [], "addresses": [],
                "crawled_pages": 0
            }

        try:
            while queue and crawled_count < self.max_pages:
                queue.sort(key=lambda x: (x[1], get_link_priority(x[0])))
                current_url, depth = queue.pop(0)
                
                current_url = normalize_url(current_url)
                if current_url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(current_url)
                
                if not await self.robots_cache.is_allowed(current_url, settings.SCRAPER_USER_AGENT, client=self.client):
                    continue
                    
                print(f"[CRAWLER] Crawling page {crawled_count + 1}: {current_url} (depth {depth})")
                
                html, method = await self.fetch_page_html(current_url)
                if not html:
                    failed_count += 1
                    if primary_failure_reason == "NO_PAGES_ACCESSED":
                        primary_failure_reason = method
                    continue
                    
                crawled_count += 1
                soup = BeautifulSoup(html, "lxml")
                
                page_emails = extract_emails(soup, current_url)
                page_phones = extract_phones(soup, current_url)
                page_socials = extract_social_links(soup, current_url)
                page_people = extract_contact_person(soup, current_url)
                
                emails.extend(page_emails)
                phones.extend(page_phones)
                socials.extend(page_socials)
                people.extend(page_people)
                
                addr_json_ld = extract_json_ld_address(soup)
                if addr_json_ld and addr_json_ld.get("address"):
                    addresses.append(addr_json_ld)
                else:
                    addr_html = extract_address_from_html(soup)
                    if addr_html and addr_html.get("address"):
                        addresses.append(addr_html)
                        
                if (len(emails) >= 1 or len(phones) >= 1 or len(addresses) >= 1):
                    print(f"[CRAWLER] Sufficient contact info found for {self.domain} after {crawled_count} pages. Ending domain crawl early.")
                    break

                if depth < self.max_depth:
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        full_link = urllib.parse.urljoin(current_url, href)
                        resolved_url = normalize_url(full_link)
                        link_domain = extract_domain(resolved_url)
                        
                        if link_domain == self.domain:
                            base_link = resolved_url.split("#")[0]
                            if base_link not in self.visited_urls and not any(q[0] == base_link for q in queue):
                                queue.append((base_link, depth + 1))
        finally:
            await self.close_playwright()
        
        return {
            "status": "SUCCESS" if crawled_count > 0 else "FAILED",
            "reason": None if crawled_count > 0 else primary_failure_reason,
            "emails": emails,
            "phones": phones,
            "socials": socials,
            "people": people,
            "addresses": addresses,
            "crawled_pages": crawled_count,
            "failed_pages": failed_count,
            "blocked_by_robots": blocked_by_robots
        }

