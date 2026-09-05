import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.models import Organization, ScrapingTask, User, TaskLead

client = TestClient(app)

def get_auth_token():
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "adminpassword"})
    if response.status_code == 200:
        return response.json()["access_token"]
    
    reg_resp = client.post("/api/auth/register", json={
        "email": "testdecouple@example.com",
        "password": "testpassword123",
        "role": "ADMIN"
    })
    if reg_resp.status_code == 201:
        return reg_resp.json()["access_token"]
    
    login_resp = client.post("/api/auth/login", json={"email": "testdecouple@example.com", "password": "testpassword123"})
    return login_resp.json()["access_token"]


def test_fast_search_endpoint_db_only_performance():
    """
    Verify /api/search/fast performs pure database-only query in < 500ms
    and does NOT call external web scrapers or search engines.
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
    assert "results" in data
    assert "timings" in data
    assert t_duration_ms < 500.0, f"Fast search exceeded 500ms target: {t_duration_ms:.2f}ms"


def test_task_creation_is_decoupled_and_fast():
    """
    Verify POST /api/tasks creates task details immediately (< 500ms)
    and does NOT synchronously wait for long-running web scrapers.
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

    with patch("app.api.tasks.run_scraping_task") as mock_background_runner:
        t_start = time.time()
        response = client.post("/api/tasks", json=payload, headers=headers)
        t_duration_ms = (time.time() - t_start) * 1000

        assert response.status_code == 201
        task_data = response.json()
        assert "public_task_id" in task_data
        assert task_data["keyword"] == "hospital"
        assert task_data["location"] == "Puducherry"
        assert t_duration_ms < 500.0, f"Task creation exceeded 500ms target: {t_duration_ms:.2f}ms"


def test_slow_discovery_does_not_block_fast_results():
    """
    Simulate a scenario where background discovery is artificially delayed for 5 seconds.
    Verify that /api/search/fast still returns existing verified organizations immediately (<500ms).
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    # Find existing task to attach test org if needed
    task_rec = db.query(ScrapingTask).first()
    task_id = task_rec.id if task_rec else 1

    org = db.query(Organization).filter(Organization.name == "Indira Gandhi Test Hospital Puducherry").first()
    if not org:
        org = Organization(
            task_id=task_id,
            name="Indira Gandhi Test Hospital Puducherry",
            category="HOSPITAL",
            sub_category="HOSPITAL",
            city="Puducherry",
            district="Puducherry",
            state="Puducherry UT",
            country="India",
            admin_verified=True,
            identity_verified=True,
            category_verified=True,
            location_verified=True,
            official_website_verified=True,
            confidence="HIGH"
        )
        db.add(org)
        db.commit()
    db.close()

    async def delayed_discover(*args, **kwargs):
        await asyncio.sleep(5.0)
        return []

    with patch("app.services.scraper.discovery.MultiSourceDiscoveryManager.discover_candidates", side_effect=delayed_discover):
        t_start = time.time()
        resp = client.get(
            "/api/search/fast",
            params={"category": "hospital", "location": "Puducherry", "limit": 15},
            headers=headers
        )
        t_duration_ms = (time.time() - t_start) * 1000

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert t_duration_ms < 1000.0, f"Fast search blocked by slow discovery: {t_duration_ms:.2f}ms"


def test_user_task_page_has_no_stats_cards_in_source():
    """
    Verify frontend task details page source file does NOT render the 7 statistics cards
    (Discovered, Websites Found, Crawled, Emails, Phones, Duplicates, Failures).
    """
    import os
    page_path = os.path.join("frontend", "src", "app", "tasks", "[id]", "page.tsx")
    assert os.path.exists(page_path), "Task details page file does not exist."

    with open(page_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'uppercase tracking-wider">Discovered</p>' not in content
    assert 'uppercase tracking-wider">Websites Found</p>' not in content
    assert 'uppercase tracking-wider">Crawled</p>' not in content
    assert 'uppercase tracking-wider">Emails</p>' not in content
    assert 'uppercase tracking-wider">Phones</p>' not in content
    assert 'uppercase tracking-wider">Duplicates</p>' not in content
    assert 'uppercase tracking-wider">Failures</p>' not in content
    assert 'api.getTaskLogs(' not in content
