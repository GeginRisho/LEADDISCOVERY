import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import ScrapingTask
from app.api.auth import seed_default_users

client = TestClient(app)

def test_health_endpoints():
    """Verify lightweight public health endpoints respond quickly with status ok."""
    # /health
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json() == {"status": "ok"}

    # /api/health
    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert res2.json() == {"status": "ok"}


def test_task_creation_idempotency():
    """Verify multiple requests with the same client_request_id do not create duplicate tasks."""
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()

    # Login to get token
    login_res = client.post("/api/auth/login", json={
        "email": "admin@leaddiscovery.com",
        "password": "admin123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client_req_id = f"test-idemp-{uuid.uuid4().hex[:10]}"
    payload = {
        "location": "Puducherry",
        "keyword": "Test Idempotency Hospital",
        "max_results": 10,
        "max_pages_per_site": 5,
        "client_request_id": client_req_id
    }

    # 1. First attempt: creates task
    res1 = client.post("/api/tasks/scrape", json=payload, headers=headers)
    assert res1.status_code == 201
    task1 = res1.json()
    task1_id = task1["id"]
    task1_public_id = task1["public_task_id"]
    assert task1_public_id.startswith("TASK-")

    # 2. Second attempt with SAME client_request_id (simulate retry on wake up)
    res2 = client.post("/api/tasks/scrape", json=payload, headers=headers)
    assert res2.status_code in (200, 201)
    task2 = res2.json()
    assert task2["id"] == task1_id, "Idempotent retry should return the identical task ID"
    assert task2["public_task_id"] == task1_public_id, "Idempotent retry should return the identical public_task_id"

    # 3. Third attempt with DIFFERENT client_request_id -> creates new task
    payload["client_request_id"] = f"test-idemp-{uuid.uuid4().hex[:10]}"
    res3 = client.post("/api/tasks/scrape", json=payload, headers=headers)
    assert res3.status_code == 201
    task3 = res3.json()
    assert task3["id"] != task1_id, "Different client_request_id should create a new distinct task"
