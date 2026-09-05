import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
# Import models to register tables on Base.metadata
from app.models.models import User, ScrapingTask, Organization, Website, SourcePage, PhoneNumber, EmailAddress, SocialLink, ScrapingLog
import os

from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables in SQLite memory DB
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply dependency override
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

from unittest.mock import patch, AsyncMock

def test_api_auth_flow_and_tasks():
    with patch("app.api.tasks.run_scraping_task", new_callable=AsyncMock):
        # 1. Register a new user
        response = client.post(
            "/api/auth/register",
            json={"email": "testuser@example.com", "password": "securepassword123"}
        )
        assert response.status_code == 201
        assert response.json()["email"] == "testuser@example.com"
        
        # 2. Login to generate JWT token
        response = client.post(
            "/api/auth/login",
            json={"email": "testuser@example.com", "password": "securepassword123"}
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Retrieve logged in user info
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "testuser@example.com"
        
        # 4. Create a scraping task
        response = client.post(
            "/api/tasks",
            json={
                "location": "Puducherry",
                "keyword": "Schools",
                "max_results": 10,
                "max_pages_per_site": 5,
                "required_fields": ["name", "email", "phone"]
            },
            headers=headers
        )
        assert response.status_code == 201
        task = response.json()
        assert task["status"] == "PENDING"
        assert "TASK-" in task["public_task_id"]
        
        # 5. Fetch all tasks history
        response = client.get("/api/tasks", headers=headers)
        assert response.status_code == 200
        tasks_list = response.json()
        assert len(tasks_list) >= 1
        assert tasks_list[0]["public_task_id"] == task["public_task_id"]
        
        # 6. Fetch logs for the task (expect at least TASK_CREATED event)
        response = client.get(f"/api/tasks/{task['public_task_id']}/logs", headers=headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) >= 1
        assert logs[0]["event_type"] == "TASK_CREATED"
        
        # 7. Cancel the task
        response = client.post(f"/api/tasks/{task['public_task_id']}/cancel", headers=headers)
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()

def test_default_seeded_users_login():
    # 1. Login as testuser@leaddiscovery.com
    response = client.post(
        "/api/auth/login",
        json={"email": "testuser@leaddiscovery.com", "password": "User@12345"}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data

    user_token = token_data["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    me_res = client.get("/api/auth/me", headers=user_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testuser@leaddiscovery.com"
    assert me_res.json()["role"] == "USER"

    # 2. Login as admin@leaddiscovery.com
    admin_response = client.post(
        "/api/auth/login",
        json={"email": "admin@leaddiscovery.com", "password": "admin123"}
    )
    assert admin_response.status_code == 200
    admin_token_data = admin_response.json()
    assert "access_token" in admin_token_data

    admin_token = admin_token_data["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    admin_me_res = client.get("/api/auth/me", headers=admin_headers)
    assert admin_me_res.status_code == 200
    assert admin_me_res.json()["email"] == "admin@leaddiscovery.com"
    assert admin_me_res.json()["role"] == "ADMIN"

def test_admin_api_endpoints_and_task_ownership():
    with patch("app.api.tasks.run_scraping_task", new_callable=AsyncMock):
        # 1. Admin login
        admin_res = client.post(
            "/api/auth/login",
            json={"email": "admin@leaddiscovery.com", "password": "admin123"}
        )
        admin_headers = {"Authorization": f"Bearer {admin_res.json()['access_token']}"}

        # 2. Normal user login
        user_res = client.post(
            "/api/auth/login",
            json={"email": "testuser@leaddiscovery.com", "password": "User@12345"}
        )
        user_headers = {"Authorization": f"Bearer {user_res.json()['access_token']}"}

        # Create task as test user
        task_res = client.post(
            "/api/tasks",
            json={
                "location": "Kanyakumari",
                "keyword": "Software Companies",
                "max_results": 10
            },
            headers=user_headers
        )
        assert task_res.status_code == 201

        # Check Admin Users endpoint
        users_list_res = client.get("/api/admin/users", headers=admin_headers)
        assert users_list_res.status_code == 200
        users = users_list_res.json()
        emails = [u["email"] for u in users]
        assert "testuser@leaddiscovery.com" in emails
        assert "admin@leaddiscovery.com" in emails

        # Check Admin Tasks endpoint
        admin_tasks_res = client.get("/api/admin/tasks", headers=admin_headers)
        assert admin_tasks_res.status_code == 200
        tasks = admin_tasks_res.json()
        assert len(tasks) >= 1
        # Task user email should be testuser@leaddiscovery.com, NOT System/Guest
        assert tasks[0]["user_email"] == "testuser@leaddiscovery.com"

        # Normal user accessing admin API should get 403 Forbidden
        forbidden_res = client.get("/api/admin/users", headers=user_headers)
        assert forbidden_res.status_code == 403
