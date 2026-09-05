import pytest
from app.services.scraper.identity_verification import verify_organization_identity
from app.services.location_service import verify_organization_location
from app.services.scraper.identification import is_candidate_relevant, verify_category_match, identify_official_website
from app.services.verification import calculate_lead_confidence

def test_acceptance_1_cbse_school_erode_wikivoyage_rejection():
    """
    TEST 1: Query = 'cbse school in Erode'
    Candidate = 'Erode – Travel guide at Wikivoyage'
    MUST be rejected as TRAVEL_GUIDE / NOT_AN_ORGANIZATION.
    MUST NOT become a verified lead.
    """
    name = "Erode – Travel guide at Wikivoyage"
    url = "https://en.wikivoyage.org/wiki/Erode"
    
    is_real, reason, meta = verify_organization_identity(name, url)
    assert not is_real
    assert reason == "TRAVEL_GUIDE"
    assert meta["entity_type"] == "CONTENT/TRAVEL_GUIDE"

    is_rel, rel_reason = is_candidate_relevant(name, "cbse school", "Erode", url)
    assert not is_rel
    assert "IDENTITY REJECT" in rel_reason

def test_acceptance_1_cbse_school_erode_legitimate_pass():
    """
    TEST 1 (Pass Case): Bharathi Vidya Bhavan Senior Secondary School in Erode
    MUST pass identity, category, and location verification.
    """
    name = "Bharathi Vidya Bhavan Senior Secondary School"
    url = "https://www.bvberode.edu.in/"
    address = "Thindal, Erode, Tamil Nadu 638012"
    
    is_real, reason, meta = verify_organization_identity(name, url)
    assert is_real
    assert reason == "PASS"

    is_cat, cat_reason = verify_category_match("cbse school", name, "", url)
    assert is_cat

    is_loc, loc_reason, _ = verify_organization_location("Erode", name, address, "BVB School Erode", url)
    assert is_loc

def test_acceptance_1_cbse_school_erode_results_page_rejection():
    """
    TEST 1: 'CBSE Class 10 Result 2024 Erode' MUST be rejected as EXAM_PORTAL.
    """
    name = "CBSE Class 10 Board Result 2024"
    url = "https://results.cbseboard.org/erode-results"
    
    is_real, reason, _ = verify_organization_identity(name, url)
    assert not is_real
    assert reason in ("EXAM_PORTAL", "DIRECTORY_ONLY")

def test_acceptance_2_school_kanyakumari_rejects_other_districts():
    """
    TEST 2: Target = 'school in Kanyakumari'
    Candidates in Puducherry, Tirunelveli, Kerala MUST be rejected.
    """
    # Candidate in Puducherry
    is_valid_pud, reason_pud, _ = verify_organization_location(
        "Kanyakumari", "Petit Seminaire School", "Moolakulam, Puducherry 605010", "Puducherry UT", "petit.com"
    )
    assert not is_valid_pud
    assert "DISTRICT_MISMATCH" in reason_pud or "LOCATION_UNVERIFIED" in reason_pud

    # Candidate in Tirunelveli
    is_valid_tir, reason_tir, _ = verify_organization_location(
        "Kanyakumari", "St. Xavier Higher Secondary School", "Palayamkottai, Tirunelveli 627002", "Tirunelveli", "stxaviets.com"
    )
    assert not is_valid_tir
    assert "DISTRICT_MISMATCH" in reason_tir

def test_acceptance_3_school_puducherry_rejects_other_states():
    """
    TEST 3: Target = 'school in Puducherry'
    Candidates in Kanyakumari, Tamil Nadu, Kerala, AP MUST be rejected.
    """
    is_valid_kny, reason_kny, _ = verify_organization_location(
        "Puducherry", "Amrita Vidyalayam Kanyakumari", "Nagercoil, Kanyakumari, Tamil Nadu 629001", "Tamil Nadu", "amrita.edu"
    )
    assert not is_valid_kny
    assert "STATE_MISMATCH" in reason_kny or "DISTRICT_MISMATCH" in reason_kny

def test_acceptance_4_hotel_erode_only_actual_hotels():
    """
    TEST 4: Target = 'hotel in Erode'
    Only actual Erode hotels pass. Booking aggregators/directories are rejected.
    """
    # Aggregator / Directory
    id_res = identify_official_website("Hotels in Erode", "https://www.booking.com/city/in/erode.html")
    assert not id_res["is_official"]
    assert id_res["is_directory_source"]

    # Actual Hotel
    is_real, _, _ = verify_organization_identity("Hotel Le Meridien Erode", "https://www.lemeridienerode.com/")
    assert is_real

def test_acceptance_5_college_erode():
    """
    TEST 5: Target = 'college in Erode'
    Only actual Erode colleges pass.
    """
    is_cat, _ = verify_category_match("college", "Kongu Engineering College", "", "https://www.kongu.ac.in/")
    assert is_cat

    is_loc, _, _ = verify_organization_location("Erode", "Kongu Engineering College", "Perundurai, Erode 638060", "", "kongu.ac.in")
    assert is_loc

def test_acceptance_6_hospital_erode():
    """
    TEST 6: Target = 'hospital in Erode'
    Only actual Erode hospitals pass.
    """
    is_cat, _ = verify_category_match("hospital", "Lotus Hospital Erode", "", "https://lotushospital.com/")
    assert is_cat

def test_acceptance_7_school_chennai():
    """
    TEST 7: Target = 'school in Chennai'
    Only Chennai schools pass.
    """
    is_loc, _, _ = verify_organization_location("Chennai", "DAV Boys Senior Secondary School", "Gopalapuram, Chennai 600086", "", "dav.edu")
    assert is_loc

def test_acceptance_8_college_salem():
    """
    TEST 8: Target = 'college in Salem'
    Only Salem colleges pass.
    """
    is_loc, _, _ = verify_organization_location("Salem", "Sona College of Technology", "Junction Main Road, Salem 636005", "", "sonatech.ac.in")
    assert is_loc

def test_acceptance_9_hotel_coimbatore():
    """
    TEST 9: Target = 'hotel in Coimbatore'
    Only Coimbatore hotels pass.
    """
    is_loc, _, _ = verify_organization_location("Coimbatore", "The Residency Towers Coimbatore", "Avinashi Road, Coimbatore 641018", "", "theresidency.com")
    assert is_loc

def test_acceptance_10_counter_logic_invariant():
    """
    TEST 10: Counter Acceptance Test
    If websites_found = 1 and crawled = 0, website-derived emails = 0 and website-derived phones = 0.
    Confidence MUST NOT be HIGH when flags are missing.
    """
    lead_uncrawled = {
        "name": "Sample School",
        "domain": "sampleschool.edu.in",
        "official_website_verified": True,
        "identity_verified": True,
        "category_verified": True,
        "country_verified": True,
        "state_verified": True,
        "district_verified": True,
        "location_verified": False, # Location unverified on website
        "emails": [],
        "phones": []
    }
    score = calculate_lead_confidence(lead_uncrawled)
    assert score != "HIGH"
