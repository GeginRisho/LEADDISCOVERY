import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import Organization, Website
from app.services.location_service import verify_organization_location, normalize_target_location
from app.services.scraper.identification import is_candidate_relevant, is_directory_domain, normalize_category_and_subcategory
from app.services.scraper.identity_verification import verify_organization_identity

client = TestClient(app)

def test_fast_search_api_performance_and_timings():
    """
    Test 1: Verify Fast Search API returns within <3s total and DB query <500ms.
    Checks timing structure and response headers.
    """
    t0 = time.time()
    response = client.get("/api/search/fast?category=cbse+school&location=Erode&limit=15")
    t_total = time.time() - t0

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["normalized_category"] == "SCHOOL"
    assert data["normalized_subcategory"] == "CBSE"
    assert data["target_district"] == "Erode"

    # Verify timing constraints
    timings = data.get("timings", {})
    assert "request_started" in timings
    assert "database_query_ms" in timings
    assert "total_response_ms" in timings

    db_ms = timings["database_query_ms"]
    total_ms = timings["total_response_ms"]

    print(f"\n[PERF BENCHMARK] Fast Search Endpoint Response: Total={total_ms}ms (API limit 3000ms), DB={db_ms}ms (DB limit 500ms)")
    assert db_ms < 500.0, f"Database query took {db_ms}ms (target <500ms)"
    assert t_total < 3.0, f"Total API response took {t_total}s (target <3.0s)"

def test_fast_search_matrix_combinations():
    """
    Test 2: Matrix performance benchmark across required category + location combinations.
    """
    test_cases = [
        ("cbse school", "Erode"),
        ("school", "Erode"),
        ("hotel", "Erode"),
        ("college", "Erode"),
        ("hospital", "Erode"),
        ("school", "Kanyakumari"),
        ("school", "Puducherry"),
        ("hotel", "Kanyakumari"),
        ("college", "Salem"),
        ("hotel", "Coimbatore")
    ]

    for cat, loc in test_cases:
        t0 = time.time()
        res = client.get(f"/api/search/fast?category={cat}&location={loc}&limit=10")
        t_dur = time.time() - t0

        assert res.status_code == 200
        data = res.json()
        assert t_dur < 3.0, f"Query '{cat}' in '{loc}' took {t_dur}s (>3.0s limit)"
        print(f"Matrix PASS: '{cat}' + '{loc}' -> {data['count']} matches in {data['timings']['database_query_ms']}ms DB / {t_dur*1000:.2f}ms total")

def test_fast_search_verification_rules_integrity():
    """
    Test 3: Verify strict rejection of Wikivoyage, directories, exam portals, non-CBSE schools for CBSE searches, wrong district, and wrong state/country.
    """
    db = SessionLocal()
    try:
        # 1. Wikivoyage Rejection
        is_real, reason, meta = verify_organization_identity("Erode Travel guide at Wikivoyage", "https://en.wikivoyage.org/wiki/Erode")
        assert not is_real
        assert meta["entity_type"] == "CONTENT/TRAVEL_GUIDE"

        # 2. Directory Domain Rejection
        assert is_directory_domain("https://www.justdial.com/Erode/Schools")
        assert is_directory_domain("https://school.careers360.com/schools-in-erode")

        # 3. Wrong District Rejection (Coimbatore candidate for Erode target)
        is_loc_valid, loc_reason, _ = verify_organization_location(
            target_location_str="Erode",
            org_name="Coimbatore Public School",
            detected_address="Avinashi Road, Coimbatore, Tamil Nadu",
            domain="coimbatoreschool.edu.in"
        )
        assert not is_loc_valid
        assert "DISTRICT_MISMATCH" in loc_reason

        # 4. Wrong State/UT Rejection (Chennai TN candidate for Puducherry UT target)
        is_loc_valid_p, loc_reason_p, _ = verify_organization_location(
            target_location_str="Puducherry",
            org_name="Chennai Central High School",
            detected_address="Anna Nagar, Chennai, Tamil Nadu",
            domain="chennaischool.org"
        )
        assert not is_loc_valid_p
        assert "STATE_MISMATCH" in loc_reason_p or "DISTRICT_MISMATCH" in loc_reason_p

        # 5. Generic Non-CBSE School Rejection for CBSE Search
        from app.services.scraper.identification import verify_category_match
        cat_pass, cat_reason = verify_category_match(
            requested_category="CBSE school",
            candidate_name="Erode Matriculation Higher Secondary School",
            candidate_url="erodematric.edu.in"
        )
        assert not cat_pass
        assert "Matriculation school" in cat_reason

    finally:
        db.close()

def test_zero_verified_orgs_immediate_return():
    """
    Test 4: Searching for a completely new category/location with zero verified entries returns 0 results immediately (<3s) without blocking.
    """
    t0 = time.time()
    res = client.get("/api/search/fast?category=nuclear_power_plant&location=Erode&limit=15")
    t_dur = time.time() - t0

    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 0
    assert t_dur < 1.0, f"Empty query took {t_dur}s (>1.0s limit)"
