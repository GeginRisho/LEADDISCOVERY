import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import User, ScrapingTask, Organization, TaskLead
from app.api.auth import seed_default_users

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_auth_and_tasks():
    db = SessionLocal()
    seed_default_users(db)

    # Get admin user
    admin_user = db.query(User).filter(User.role == "ADMIN").first()

    # Create or get normal user
    normal_user = db.query(User).filter(User.email == "history_test_user@example.com").first()
    if not normal_user:
        from app.core.security import get_password_hash
        normal_user = User(
            email="history_test_user@example.com",
            hashed_password=get_password_hash("password123"),
            role="USER",
            status="ACTIVE"
        )
        db.add(normal_user)
        db.commit()
        db.refresh(normal_user)

    # Create test task with null optional fields if not exists
    task_null_fields = db.query(ScrapingTask).filter(ScrapingTask.public_task_id == "TASK-REGRESSION-NULL").first()
    if not task_null_fields:
        task_null_fields = ScrapingTask(
            user_id=normal_user.id,
            public_task_id="TASK-REGRESSION-NULL",
            location="Madurai",
            keyword="Test Keyword",
            radius=None,
            max_results=50,
            max_pages_per_site=10,
            requested_fields=None,
            required_fields=None,
            error_info=None,
            status="COMPLETED"
        )
        db.add(task_null_fields)
        db.commit()

    # Create admin task if not exists
    task_admin = db.query(ScrapingTask).filter(ScrapingTask.public_task_id == "TASK-REGRESSION-ADMIN").first()
    if not task_admin:
        task_admin = ScrapingTask(
            user_id=admin_user.id,
            public_task_id="TASK-REGRESSION-ADMIN",
            location="Chennai",
            keyword="Colleges",
            status="RUNNING"
        )
        db.add(task_admin)
        db.commit()

    # Create an organization and attach via TaskLead if not exists
    org = db.query(Organization).filter(Organization.name == "Regression University").first()
    if not org:
        org = Organization(
            task_id=task_admin.id,
            name="Regression University",
            category="Colleges",
            district="Chennai",
            state="Tamil Nadu",
            country="India"
        )
        db.add(org)
        db.commit()

    tl = db.query(TaskLead).filter(TaskLead.task_id == task_admin.id, TaskLead.organization_id == org.id).first()
    if not tl:
        task_lead = TaskLead(
            task_id=task_admin.id,
            organization_id=org.id,
            qualification_status="QUALIFIED"
        )
        db.add(task_lead)
        db.commit()

    normal_user_id = normal_user.id
    db.close()

    # Get tokens
    admin_res = client.post("/api/auth/login", json={"email": "admin@leaddiscovery.com", "password": "admin123"})
    admin_token = admin_res.json()["access_token"]

    normal_res = client.post("/api/auth/login", json={"email": "history_test_user@example.com", "password": "password123"})
    normal_token = normal_res.json()["access_token"]

    return {
        "admin_token": admin_token,
        "normal_token": normal_token,
        "normal_user_id": normal_user_id
    }

def test_task_history_unauthenticated_returns_401():
    """Unauthenticated request to /api/tasks returns 401."""
    res = client.get("/api/tasks")
    assert res.status_code == 401

def test_task_history_admin_sees_all_tasks(setup_auth_and_tasks):
    """Admin user can fetch task history and receives 200 with tasks."""
    headers = {"Authorization": f"Bearer {setup_auth_and_tasks['admin_token']}"}
    res = client.get("/api/tasks?page=1&limit=20", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify task attributes
    task = next((t for t in data if t["public_task_id"] == "TASK-REGRESSION-ADMIN"), None)
    assert task is not None
    assert task["keyword"] == "Colleges"
    assert task["location"] == "Chennai"
    assert task["status"] == "RUNNING"
    assert "lead_count" in task
    assert "user_email" in task
    assert "social_count" in task

def test_task_history_alias_endpoint(setup_auth_and_tasks):
    """GET /api/tasks/history route alias works and returns 200."""
    headers = {"Authorization": f"Bearer {setup_auth_and_tasks['admin_token']}"}
    res = client.get("/api/tasks/history?page=1&limit=10", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_task_history_normal_user_sees_permitted_only(setup_auth_and_tasks):
    """Normal user sees only their own permitted tasks."""
    headers = {"Authorization": f"Bearer {setup_auth_and_tasks['normal_token']}"}
    res = client.get("/api/tasks", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    for task in data:
        assert task["user_id"] == setup_auth_and_tasks["normal_user_id"]

def test_task_history_null_optional_fields_no_crash(setup_auth_and_tasks):
    """Null optional fields (radius, requested_fields, etc.) serialize safely."""
    headers = {"Authorization": f"Bearer {setup_auth_and_tasks['admin_token']}"}
    res = client.get("/api/tasks?limit=50", headers=headers)
    assert res.status_code == 200
    task = next((t for t in res.json() if t["public_task_id"] == "TASK-REGRESSION-NULL"), None)
    assert task is not None
    assert task["radius"] is None
    assert task["requested_fields"] is None

def test_task_history_pagination(setup_auth_and_tasks):
    """Pagination parameters page and limit work correctly."""
    headers = {"Authorization": f"Bearer {setup_auth_and_tasks['admin_token']}"}
    res1 = client.get("/api/tasks?page=1&limit=2", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) <= 2

    res2 = client.get("/api/tasks?page=2&limit=2", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2) <= 2
    if len(data1) > 0 and len(data2) > 0:
        assert data1[0]["id"] != data2[0]["id"]

def test_task_history_empty_query(setup_auth_and_tasks):
    """Querying page 999999 returns empty list [] with 200, never 500."""
    headers = {"Authorization": f"Bearer {setup_auth_and_tasks['admin_token']}"}
    res = client.get("/api/tasks?page=999999&limit=50", headers=headers)
    assert res.status_code == 200
    assert res.json() == []
