from app.services.scraper.robots import is_safe_url
from app.services.scraper.identification import normalize_url, extract_domain

def test_url_normalization():
    assert normalize_url("example.com") == "https://example.com/"
    assert normalize_url("http://example.com/about?query=1") == "http://example.com/about"
    assert normalize_url("https://www.example.org/path/subpage/#anchor") == "https://www.example.org/path/subpage/"

def test_extract_domain():
    assert extract_domain("https://www.example.com/about") == "example.com"
    assert extract_domain("http://school.edu.in/home") == "school.edu.in"
    assert extract_domain("http://sub.domain.example.org/") == "sub.domain.example.org"

import pytest

@pytest.mark.asyncio
async def test_ssrf_safety_protection():
    # 1. Test public domains (should be safe)
    assert await is_safe_url("https://google.com") is True
    assert await is_safe_url("https://wikipedia.org/wiki/Main_Page") is True
    
    # 2. Test loopback/local hostnames and IPs (should be unsafe)
    assert await is_safe_url("http://localhost") is False
    assert await is_safe_url("https://127.0.0.1") is False
    assert await is_safe_url("http://[::1]") is False
    assert await is_safe_url("http://127.0.0.99") is False
    
    # 3. Test private IP networks (should be unsafe)
    assert await is_safe_url("http://192.168.1.1") is False
    assert await is_safe_url("http://10.0.0.2") is False
    assert await is_safe_url("http://172.16.5.5") is False
    
    # 4. Test link-local & cloud metadata IPs (should be unsafe)
    assert await is_safe_url("http://169.254.169.254") is False
    assert await is_safe_url("http://[fe80::1]") is False
    
    # 5. Test invalid schemes (should be unsafe)
    assert await is_safe_url("file:///etc/passwd") is False
    assert await is_safe_url("javascript:alert(1)") is False
    assert await is_safe_url("ftp://ftp.example.com") is False
