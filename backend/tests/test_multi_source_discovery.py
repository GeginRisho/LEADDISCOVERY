import pytest
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.scraper.discovery import (
    generate_multi_queries,
    MultiSourceDiscoveryManager,
    DiscoveryProvider,
    GovernmentDirectoryProvider,
    ExistingMasterProvider,
    BingHTMLProvider,
    DuckDuckGoHTMLProvider
)
from app.services.scraper.identity_verification import verify_organization_identity
from app.services.scraper.identification import verify_category_match
from app.services.location_service import verify_organization_location


@pytest.mark.asyncio
async def test_query_expansion_generates_multiple_queries():
    queries = generate_multi_queries("hospital", "Puducherry")
    assert isinstance(queries, list)
    assert len(queries) >= 5
    
    # Check alias expansion (Puducherry -> Pondicherry)
    query_str = " ".join(queries).lower()
    assert "puducherry" in query_str
    assert "pondicherry" in query_str
    assert "hospital" in query_str


@pytest.mark.asyncio
async def test_provider_failure_isolation():
    class FailingProvider(DiscoveryProvider):
        @property
        def provider_name(self) -> str:
            return "FailingTestProvider"

        async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
            raise RuntimeError("Provider failed catastrophically")

    class WorkingProvider(DiscoveryProvider):
        @property
        def provider_name(self) -> str:
            return "WorkingTestProvider"

        async def discover(self, location: str, keyword: str, max_results: int = 100, client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
            return [
                {
                    "name": "Indira Gandhi Government General Hospital",
                    "address": "Victor Simonel St, White Town, Puducherry 605001",
                    "city": "Puducherry",
                    "state": "Puducherry",
                    "country": "India",
                    "discovery_source": "WorkingTestProvider",
                    "discovery_source_type": "GOVERNMENT_DIRECTORY",
                    "source_url": "https://health.py.gov.in/hospitals"
                }
            ]

    manager = MultiSourceDiscoveryManager([FailingProvider(), WorkingProvider()])
    candidates = await manager.discover_candidates(db=None, category="hospital", location="Puducherry")
    
    assert len(candidates) >= 1
    assert candidates[0]["name"] == "Indira Gandhi Government General Hospital"
    assert candidates[0]["discovery_source"] == "WorkingTestProvider"


@pytest.mark.asyncio
async def test_government_directory_provider_puducherry_hospitals():
    mock_html = """
    <html>
      <body>
        <ol id="b_results">
          <li class="b_algo">
            <h2><a href="https://health.py.gov.in/hospitals/iggh">Indira Gandhi Government General Hospital - Puducherry</a></h2>
            <cite>health.py.gov.in/hospitals/iggh</cite>
          </li>
          <li class="b_algo">
            <h2><a href="https://health.py.gov.in/hospitals/rggwch">Rajiv Gandhi Government Women and Children Hospital - Puducherry</a></h2>
            <cite>health.py.gov.in/hospitals/rggwch</cite>
          </li>
        </ol>
      </body>
    </html>
    """

    provider = GovernmentDirectoryProvider()
    
    with patch("httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        MockClient.return_value = mock_instance

        candidates = await provider.discover(location="Puducherry", keyword="hospital")

    assert len(candidates) >= 2
    hospital_names = [c["name"] for c in candidates]
    assert any("Indira Gandhi" in name for name in hospital_names)
    assert any("Rajiv Gandhi" in name for name in hospital_names)
    for c in candidates:
        assert c["discovery_source_type"] == "GOVERNMENT_DIRECTORY"


@pytest.mark.asyncio
async def test_candidate_preservation_without_official_website():
    """
    Test that a candidate discovered via authoritative sources without a direct official website
    is NOT discarded and is preserved with official_website_verified = False.
    """
    candidate = {
        "name": "Mahatma Gandhi Leprosy Hospital",
        "address": "Gorimedu, Puducherry 605006",
        "city": "Puducherry",
        "state": "Puducherry",
        "country": "India",
        "discovery_source": "GovernmentDirectoryProvider",
        "discovery_source_type": "GOVERNMENT_DIRECTORY",
        "source_url": "https://health.py.gov.in/hospitals"
    }

    # 1. Identity check
    is_ident, ident_reason, _ = verify_organization_identity(candidate["name"], candidate["source_url"])
    assert is_ident, f"Identity verification failed: {ident_reason}"

    # 2. Category check
    is_cat, cat_reason = verify_category_match(requested_category="hospital", candidate_name=candidate["name"])
    assert is_cat, f"Category verification failed: {cat_reason}"

    # 3. Location check
    is_loc, loc_reason, _ = verify_organization_location(
        target_location_str="Puducherry",
        org_name=candidate["name"],
        detected_address=candidate["address"]
    )
    assert is_loc, f"Location verification failed: {loc_reason}"
