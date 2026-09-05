from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DiscoveryProvider(ABC):
    @abstractmethod
    async def discover(self, location: str, keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Discover organization candidates based on location and keyword.
        
        Returns:
            List[Dict[str, Any]]: A list of dicts with:
                - name: str (Organization name)
                - category: Optional[str] (Business category)
                - location: Optional[str] (Location detail)
                - possible_website: Optional[str] (Domain or full URL candidate)
                - source_url: str (Search query result page URL or directory URL)
                - discovery_source: str (Name of the provider, e.g. DuckDuckGo)
                - confidence: str (HIGH, MEDIUM, LOW quality estimate of website official status)
        """
        pass
