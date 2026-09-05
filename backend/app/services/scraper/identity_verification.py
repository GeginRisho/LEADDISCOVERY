import re
import urllib.parse
from typing import Dict, Any, Tuple, List, Optional

# Machine-readable rejection codes
REJECTION_NOT_AN_ORGANIZATION = "NOT_AN_ORGANIZATION"
REJECTION_TRAVEL_GUIDE = "TRAVEL_GUIDE"
REJECTION_ENCYCLOPEDIA = "ENCYCLOPEDIA_ARTICLE"
REJECTION_DIRECTORY = "DIRECTORY_ONLY"
REJECTION_AGGREGATOR = "AGGREGATOR_ONLY"
REJECTION_ARTICLE = "ARTICLE_ONLY"
REJECTION_RESULTS_PORTAL = "RESULTS_PORTAL"
REJECTION_EXAM_PORTAL = "EXAM_PORTAL"
REJECTION_RANKING_PAGE = "RANKING_PAGE"
REJECTION_REVIEW_PAGE = "REVIEW_PAGE"
REJECTION_CATEGORY_LISTING = "CATEGORY_LISTING"
REJECTION_SOCIAL_MEDIA = "SOCIAL_MEDIA_PAGE"
REJECTION_GOVERNMENT_PORTAL = "GOVERNMENT_PORTAL_ONLY"

# Schema.org JSON-LD Types representing real physical/legal organizations
ORGANIZATION_SCHEMA_TYPES = {
    "organization", "localbusiness", "school", "educationalorganization",
    "elementaryschool", "highschool", "middleschool", "preschool",
    "collegeoruniversity", "hotel", "lodgingbusiness", "resort",
    "hospital", "medicalorganization", "medicalclinic", "physician",
    "restaurant", "foodestablishment", "corporation", "businessentity"
}

# Schema.org JSON-LD Types representing articles, content, listing pages, search pages
CONTENT_SCHEMA_TYPES = {
    "webpage", "article", "newsarticle", "blogposting", "itempage",
    "searchresultspage", "collectionpage", "guide", "aboutpage",
    "qapage", "faqpage", "profilepage", "discussionforumposting"
}

# Title & Content patterns indicating a Travel Guide or Tourism Article
TRAVEL_GUIDE_TITLE_PATTERNS = [
    r'travel guide', r'wikivoyage', r'wikitravel', r'things to do in',
    r'places to visit in', r'tourist attractions', r'sightseeing in',
    r'travel tips', r'city guide', r'visitor guide', r'tourism in', r'travelogue'
]

# Title & Content patterns indicating an Encyclopedia or Reference Entry
ENCYCLOPEDIA_TITLE_PATTERNS = [
    r'wikipedia', r'wiktionary', r'encyclopedia', r'definition & meaning',
    r'meaning of', r'overview of', r'history of'
]

# Title & Content patterns indicating a Directory, Aggregator, Ranking, or Listing
LISTING_TITLE_PATTERNS = [
    r'list of\b', r'top \d+\b', r'\d+ best\b', r'best \w+ in', r'directory of',
    r'ranking of', r'compare ', r'reviews of', r'yellow pages', r'find \w+ near',
    r'search results', r'listings in', r'popular \w+ in'
]

# Title & Content patterns indicating Exam Results, Syllabus, Board portals & Admission articles
EXAM_PORTAL_TITLE_PATTERNS = [
    r'result 20\d\d', r'exam result', r'board result', r'date sheet',
    r'datesheet', r'admit card', r'answer key', r'sample paper',
    r'question paper', r'syllabus', r'cutoff', r'hall ticket',
    r'admission process', r'admission in', r'admissions in', r'admission guidelines',
    r'fee structure', r'fee details', r'how to apply', r'eligibility criteria'
]

# URL Path segments indicating non-organization pages
CONTENT_PATH_PATTERNS = [
    r'/wiki/', r'/travel-guide/', r'/things-to-do/', r'/places-to-visit/',
    r'/article/', r'/articles/', r'/blog/', r'/blogs/', r'/news/',
    r'/listing/', r'/listings/', r'/directory/', r'/search/', r'/results/',
    r'/category/', r'/categories/', r'/exam/', r'/syllabus/', r'/admit-card/',
    r'/question-paper/', r'/date-sheet/', r'/reviews/', r'/comparison/'
]

def verify_organization_identity(
    name: str,
    url: str = "",
    snippet: str = "",
    html_text: str = "",
    jsonld_data: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Generically verifies whether a candidate represents a REAL PHYSICAL/LEGAL ORGANIZATION
    versus a Search/Discovery Content page (Travel guide, Wikipedia, Article, Directory, 
    Exam portal, Board results, Ranking page, etc.).
    
    Uses MULTI-SIGNAL DEEP INSPECTION:
    - Candidate name & title formatting
    - Canonical URL & path structure
    - Meta description / Snippet content
    - Schema.org JSON-LD structural types
    - Breadcrumb taxonomy & page layout clues
    
    Returns:
        (identity_verified: bool, rejection_reason: str, metadata: dict)
    """
    metadata = {
        "entity_type": "UNKNOWN",
        "identity_verified": False,
        "category_verified": False,
        "official_website_verified": False,
        "rejection_reason": None,
        "schema_types": [],
        "signals_evaluated": []
    }

    if not name or len(name.strip()) < 3:
        metadata["rejection_reason"] = REJECTION_NOT_AN_ORGANIZATION
        return False, REJECTION_NOT_AN_ORGANIZATION, metadata

    name_lower = name.lower().strip()
    url_lower = (url or "").lower().strip()
    snippet_lower = (snippet or "").lower().strip()
    combined_text = f"{name_lower} {snippet_lower} {html_text[:1000].lower()}"

    # Extract JSON-LD Schema.org Types if available
    found_schema_types = set()
    if jsonld_data:
        for item in jsonld_data:
            if isinstance(item, dict):
                stype = item.get("@type")
                if isinstance(stype, str):
                    found_schema_types.add(stype.lower())
                elif isinstance(stype, list):
                    found_schema_types.update([s.lower() for s in stype if isinstance(s, str)])
    
    metadata["schema_types"] = list(found_schema_types)

    # 1. TRAVEL GUIDE CHECK
    for pattern in TRAVEL_GUIDE_TITLE_PATTERNS:
        if re.search(pattern, combined_text) or (url_lower and re.search(pattern, url_lower)):
            metadata["entity_type"] = "CONTENT/TRAVEL_GUIDE"
            metadata["rejection_reason"] = REJECTION_TRAVEL_GUIDE
            return False, REJECTION_TRAVEL_GUIDE, metadata

    # 2. ENCYCLOPEDIA / REFERENCE CHECK
    for pattern in ENCYCLOPEDIA_TITLE_PATTERNS:
        if re.search(pattern, name_lower) or (url_lower and ("wikipedia.org" in url_lower or "wiktionary.org" in url_lower or "/wiki/" in url_lower)):
            metadata["entity_type"] = "CONTENT/ENCYCLOPEDIA"
            metadata["rejection_reason"] = REJECTION_ENCYCLOPEDIA
            return False, REJECTION_ENCYCLOPEDIA, metadata

    # 3. EXAM PORTAL / BOARD RESULT / SYLLABUS CHECK
    for pattern in EXAM_PORTAL_TITLE_PATTERNS:
        if re.search(pattern, name_lower):
            metadata["entity_type"] = "CONTENT/EXAM_PORTAL"
            metadata["rejection_reason"] = REJECTION_EXAM_PORTAL
            return False, REJECTION_EXAM_PORTAL, metadata

    # 4. MULTI-ITEM DIRECTORY / AGGREGATOR / RANKING LIST CHECK
    for pattern in LISTING_TITLE_PATTERNS:
        if re.search(pattern, name_lower):
            metadata["entity_type"] = "CONTENT/RANKING_OR_DIRECTORY"
            metadata["rejection_reason"] = REJECTION_RANKING_PAGE
            return False, REJECTION_RANKING_PAGE, metadata

    # 5. URL PATH PATTERN INSPECTION
    if url_lower:
        parsed = urllib.parse.urlparse(url_lower)
        path = parsed.path
        for path_pat in CONTENT_PATH_PATTERNS:
            if re.search(path_pat, path):
                # Verify if path indicates a listing/article index rather than org contact page
                if not any(org_kw in path for org_kw in ["about", "contact", "location", "branch", "campus"]):
                    metadata["entity_type"] = "CONTENT/CATEGORY_PATH"
                    metadata["rejection_reason"] = REJECTION_DIRECTORY
                    return False, REJECTION_DIRECTORY, metadata

    # 6. SCHEMA.ORG TYPE EVALUATION (IF PRESENT)
    if found_schema_types:
        has_org_schema = bool(found_schema_types.intersection(ORGANIZATION_SCHEMA_TYPES))
        has_content_schema = bool(found_schema_types.intersection(CONTENT_SCHEMA_TYPES))
        
        if has_content_schema and not has_org_schema:
            metadata["entity_type"] = "CONTENT/PAGE_SCHEMA"
            metadata["rejection_reason"] = REJECTION_ARTICLE
            return False, REJECTION_ARTICLE, metadata

    # 7. SPECIFIC NON-ORGANIZATION TITLE FORMATS
    # E.g., "Erode - Travel guide at Wikivoyage", "CBSE Result 2024", "Top Schools List"
    if " – travel guide" in name_lower or " - travel guide" in name_lower or " travel guide at " in name_lower:
        metadata["entity_type"] = "CONTENT/TRAVEL_GUIDE"
        metadata["rejection_reason"] = REJECTION_TRAVEL_GUIDE
        return False, REJECTION_TRAVEL_GUIDE, metadata

    # If candidate passes identity checks
    metadata["entity_type"] = "REAL_ORGANIZATION"
    metadata["identity_verified"] = True
    return True, "PASS", metadata
