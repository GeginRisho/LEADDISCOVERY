import socket
import ipaddress
import urllib.parse
import asyncio
from urllib.robotparser import RobotFileParser
import httpx
from typing import Optional, Dict, Any, Union
from app.core.config import settings

async def is_safe_url(url: str) -> bool:
    """
    Validates a URL against Server-Side Request Forgery (SSRF).
    Ensures scheme is http/https and resolved IPs do not belong to local/private ranges.
    Uses non-blocking asyncio DNS resolution.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        hostname_lower = hostname.lower()
        
        # Immediate block on localhost-like hostnames
        if hostname_lower in ("localhost", "localhost.localdomain", "loopback", "127.0.0.1", "[::1]"):
            return False
            
        # Non-blocking async DNS resolution with 2.0s hard timeout
        loop = asyncio.get_event_loop()
        try:
            addr_infos = await asyncio.wait_for(
                loop.getaddrinfo(hostname, None),
                timeout=2.0
            )
        except Exception:
            return False

        if not addr_infos:
            return False

        for info in addr_infos:
            ip_str = info[4][0]
            if "%" in ip_str:
                ip_str = ip_str.split("%")[0]
                
            ip = ipaddress.ip_address(ip_str)
            
            if ip.version == 6 and str(ip).startswith("64:ff9b:"):
                continue

            if (ip.is_private or 
                ip.is_loopback or 
                ip.is_link_local or 
                ip.is_multicast or 
                ip.is_reserved or 
                ip.is_unspecified):
                return False
                
        return True
    except Exception:
        return False

async def safe_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_redirects: int = 3,
    **kwargs
) -> httpx.Response:
    """
    Executes an HTTP request with manual redirect following.
    Revalidates the destination URL at each hop against SSRF blocklists.
    Retries with verify=False if SSL certificate verification fails on a safe public URL.
    """
    current_url = url
    method = method.upper()
    
    for redirect_hop in range(max_redirects + 1):
        if not await is_safe_url(current_url):
            raise ValueError(f"SSRF block triggered: URL {current_url} is not safe.")
            
        kwargs["follow_redirects"] = False

        try:
            response = await client.request(method, current_url, **kwargs)
        except (httpx.SSLError, httpx.ConnectError) as ssl_err:
            err_msg = str(ssl_err).lower()
            if "ssl" in err_msg or "certificate" in err_msg or isinstance(ssl_err, httpx.SSLError):
                ssl_kwargs = dict(kwargs)
                ssl_kwargs["verify"] = False
                response = await client.request(method, current_url, **ssl_kwargs)
            else:
                raise
        
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("Location")
            if not redirect_url:
                return response
            current_url = urllib.parse.urljoin(current_url, redirect_url)
            if response.status_code in (301, 302, 303):
                method = "GET"
                kwargs.pop("content", None)
                kwargs.pop("data", None)
                kwargs.pop("json", None)
        else:
            return response
            
    raise httpx.TooManyRedirects(f"Exceeded maximum of {max_redirects} redirects.")

class RobotsCache:
    """
    Fetches, parses, and caches robots.txt rules for scraped domains.
    Handles caching to avoid fetching robots.txt for every subpage request.
    """
    def __init__(self):
        self.cache: Dict[str, Optional[RobotFileParser]] = {}

    async def is_allowed(self, url: str, user_agent: str = "*", client: Optional[httpx.AsyncClient] = None) -> bool:
        """
        Determines whether a crawl path is permitted under robots.txt.
        Uses in-memory cache and 3.0s hard timeout.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
                
            domain = parsed.netloc.lower()
            
            if domain in self.cache:
                rp = self.cache[domain]
                if rp is None:
                    return True # Permitted by default if failed previously
                return rp.can_fetch(user_agent, url)
                
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            if not await is_safe_url(robots_url):
                self.cache[domain] = None
                return False
                
            rp = RobotFileParser()
            headers = {"User-Agent": user_agent}
            
            async def fetch_robots():
                if client is not None:
                    response = await safe_request(client, "GET", robots_url, headers=headers)
                else:
                    async with httpx.AsyncClient(timeout=3.0, verify=False) as temp_client:
                        response = await safe_request(temp_client, "GET", robots_url, headers=headers)
                return response

            try:
                response = await asyncio.wait_for(fetch_robots(), timeout=3.0)
                if response.status_code == 200 and response.text:
                    rp.parse(response.text.splitlines())
                    self.cache[domain] = rp
                    return rp.can_fetch(user_agent, url)
                else:
                    self.cache[domain] = None
                    return True
            except Exception:
                self.cache[domain] = None
                return True
        except Exception:
            return True

