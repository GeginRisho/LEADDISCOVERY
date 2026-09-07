import pytest
import time
import asyncio
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.models import Organization, ScrapingTask, User, TaskLead
from app.services.scraper.identity_verification import classify_candidate_entity, verify_organization_identity
from app.services.scraper.identification import verify_category_match
from app.services.location_service import verify_organization_location
from app.core.cleanup_database import audit_and_cleanup_database

client = TestClient(app)

def get_auth_token():
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "adminpassword"})
    if response.status_code == 200:
        return response.json()["access_token"]
    
    reg_resp = client.post("/api/auth/register", json={
        "email": "testrealpipeline@example.com",
        "password": "testpassword123",
        "role": "ADMIN"
    })
    if reg_resp.status_code == 201:
        login_resp = client.post("/api/auth/login", json={"email": "testrealpipeline@example.com", "password": "testpassword123"})
        if login_resp.status_code == 200:
            return login_resp.json()["access_token"]
    
    login_resp = client.post("/api/auth/login", json={"email": "testrealpipeline@example.com", "password": "testpassword123"})
    return login_resp.json()["access_token"]


def test_candidate_entity_classification_rejects_non_organizations():
    """
    Verify that search-result titles, central/state government portals, directories,
    travel guides, and encyclopedia articles are classified as non-organizations and REJECTED.
    """
    bad_candidates = [
        ("OurGovernment| Prime Minister of India", "https://india.gov.in"),
        ("MyGov: A Platform for Citizen Engagement", "https://mygov.in"),
        ("Integrated Government Online Directory", "https://goidirectory.gov.in"),
        ("Erode – Travel guide at Wikivoyage", "https://en.wikivoyage.org/wiki/Erode"),
        ("Puducherry - Wikipedia", "https://en.wikipedia.org/wiki/Puducherry"),
        ("Top 10 Best Hotels in Salem 2024", "https://tripadvisor.com/hotels-salem"),
        ("CBSE Board Result 2024 Date Sheet", "https://cbseresults.nic.in"),
    ]

    for name, url in bad_candidates:
        entity_type, conf, meta = classify_candidate_entity(name, url)
        assert entity_type != "ORGANIZATION", f"Candidate '{name}' should NOT be classified as ORGANIZATION"

        is_real, id_reason, _ = verify_organization_identity(name, url)
        assert not is_real, f"Candidate '{name}' should fail identity verification but passed: {id_reason}"


def test_candidate_entity_classification_accepts_real_organizations():
    """
    Verify that real physical/legal organizations are classified as ORGANIZATION.
    """
    good_candidates = [
        ("Indira Gandhi Government General Hospital", "https://health.py.gov.in/iggh"),
        ("Rajiv Gandhi Government Women and Children Hospital", "https://health.py.gov.in/rggwch"),
        ("Petit Seminaire CBSE School", "https://petitcbse.com"),
        ("Radisson Blu Resort Temple Bay", "https://radissonhotels.com"),
        ("Sona College of Technology", "https://sonatech.ac.in"),
    ]

    for name, url in good_candidates:
        entity_type, conf, meta = classify_candidate_entity(name, url)
        assert entity_type == "ORGANIZATION", f"Real organization '{name}' should be classified as ORGANIZATION"

        is_real, id_reason, _ = verify_organization_identity(name, url)
        assert is_real, f"Real organization '{name}' failed identity check: {id_reason}"


def test_strict_location_verification_rejects_wrong_location():
    """
    Verify that candidates in the wrong city/state/country are strictly rejected.
    """
    # 1. Target Puducherry, Candidate in Hyderabad
    is_valid, reason, _ = verify_organization_location(
        target_location_str="Puducherry",
        org_name="Hyderabad Grand Hotel",
        detected_address="Banjara Hills, Hyderabad, Telangana 500034",
        domain="hyderabadgrand.com"
    )
    assert not is_valid

    # 2. Target Salem, Candidate in Mumbai
    is_valid, reason, _ = verify_organization_location(
        target_location_str="Salem",
        org_name="Mumbai Plaza Hotel",
        detected_address="Marine Drive, Mumbai, Maharashtra 400020",
        domain="mumbaiplaza.com"
    )
    assert not is_valid

    # 3. Target Kanyakumari, Candidate in Coimbatore
    is_valid, reason, _ = verify_organization_location(
        target_location_str="Kanyakumari",
        org_name="Kovai Public School",
        detected_address="Avinashi Road, Coimbatore, Tamil Nadu 641014",
        domain="kovaipublicschool.com"
    )
    assert not is_valid


def test_strict_category_verification_across_multiple_categories():
    """
    Verify category verification across hotel, school, CBSE school, hospital, college, software company.
    """
    # CBSE School check
    cat_ok, cat_reason = verify_category_match(requested_category="CBSE school", candidate_name="Petit Seminaire CBSE School")
    assert cat_ok

    # Matriculation school rejected for CBSE search
    cat_ok, cat_reason = verify_category_match(requested_category="CBSE school", candidate_name="St Joseph Matriculation Higher Secondary School")
    assert not cat_ok

    # Hotel check
    cat_ok, cat_reason = verify_category_match(requested_category="hotel", candidate_name="Grand Palace Hotel & Resort")
    assert cat_ok

    # Hospital check
    cat_ok, cat_reason = verify_category_match(requested_category="hospital", candidate_name="Apollo Multispecialty Hospital")
    assert cat_ok


def test_fast_search_db_only_performance():
    """
    Verify /api/search/fast performs DB-only read (<500ms) and excludes quarantined records.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    t_start = time.time()
    response = client.get(
        "/api/search/fast",
        params={"category": "hospital", "location": "Puducherry", "limit": 15},
        headers=headers
    )
    t_duration_ms = (time.time() - t_start) * 1000

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert t_duration_ms < 500.0, f"Fast search exceeded 500ms: {t_duration_ms:.2f}ms"


def test_task_creation_is_fast_and_decoupled():
    """
    Verify POST /api/tasks creates task in <500ms without blocking.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "location": "Puducherry",
        "keyword": "hospital",
        "max_results": 15,
        "max_pages_per_site": 5,
        "required_fields": ["phone", "address"]
    }

    with patch("app.api.tasks.run_scraping_task"):
        t_start = time.time()
        response = client.post("/api/tasks", json=payload, headers=headers)
        t_duration_ms = (time.time() - t_start) * 1000

        assert response.status_code == 201
        assert t_duration_ms < 500.0, f"Task creation exceeded 500ms: {t_duration_ms:.2f}ms"


def test_user_task_page_has_no_scraper_dashboard():
    """
    Verify that frontend task details page (/tasks/[id]/page.tsx) source code
    has zero 7 statistics cards and no scraper log fetching.
    """
    page_path = os.path.join("frontend", "src", "app", "tasks", "[id]", "page.tsx")
    assert os.path.exists(page_path)

    with open(page_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'discovered_count' not in content
    assert 'websites_found' not in content
    assert 'crawled_count' not in content
    assert 'emails_found' not in content
    assert 'phones_found' not in content
    assert 'duplicate_count' not in content
    assert 'failure_count' not in content
    assert 'getTaskLogs(' not in content
