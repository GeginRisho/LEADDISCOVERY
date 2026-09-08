import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import datetime

from app.main import app
from app.core.database import Base, engine, get_db, SessionLocal
from app.models.models import User, Organization, ScrapingTask
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)

TEST_ORG_NAMES = [
    "Test Hotel Puducherry",
    "Hotel Chennai Admin",
    "Hotel Puducherry Scraper",
    "Target Hotel Puducherry",
    "Puducherry Heritage Hotel",
    "Puducherry High School",
    "Fake Puducherry Hotel"
]

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Organization).filter(Organization.name.in_(TEST_ORG_NAMES)).delete(synchronize_session=False)
        db.query(User).filter(User.email.in_(["admin_instant@leaddiscovery.com", "user_instant@leaddiscovery.com"])).delete(synchronize_session=False)
        db.commit()

        # Create admin user
        admin = User(
            email="admin_instant@leaddiscovery.com",
            hashed_password=get_password_hash("admin123"),
            role="ADMIN",
            status="ACTIVE"
        )
        # Create normal user
        user = User(
            email="user_instant@leaddiscovery.com",
            hashed_password=get_password_hash("user123"),
            role="USER",
            status="ACTIVE"
        )
        db.add_all([admin, user])
        db.commit()
    finally:
        db.close()

    yield

    db = SessionLocal()
    try:
        db.query(Organization).filter(Organization.name.in_(TEST_ORG_NAMES)).delete(synchronize_session=False)
        db.query(User).filter(User.email.in_(["admin_instant@leaddiscovery.com", "user_instant@leaddiscovery.com"])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

def get_user_headers(email: str = "user_instant@leaddiscovery.com"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.id})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

def test_admin_verified_result_is_returned_immediately_on_task_creation():
    """
    Requirements 28 & 34:
    Admin creates and verifies 'Test Hotel Puducherry'.
    User creates task 'hotel' + 'Puducherry'.
    POST /api/tasks/scrape returns fast_verified_results containing 'Test Hotel Puducherry' immediately.
    """
    db = SessionLocal()
    try:
        org = Organization(
            name="Test Hotel Puducherry",
            category="HOTEL",
            country="India",
            state="Puducherry",
            district="Puducherry",
            city="Puducherry",
            admin_verified=True,
            confidence="HIGH",
            source_type="ADMIN_VERIFIED",
            verification_method="ADMIN",
            official_website_url="https://testhotel.com"
        )
        db.add(org)
        db.commit()
    finally:
        db.close()

    headers = get_user_headers("user_instant@leaddiscovery.com")
    payload = {
        "keyword": "hotel",
        "location": "Puducherry",
        "max_results": 15
    }

    res = client.post("/api/tasks/scrape", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert "public_task_id" in data
    assert "fast_verified_results" in data
    assert data["fast_verified_results"] is not None
    assert len(data["fast_verified_results"]) >= 1

    found_names = [o["name"] for o in data["fast_verified_results"]]
    assert "Test Hotel Puducherry" in found_names

def test_location_priority_in_task_creation():
    """
    Requirement 29:
    Admin verified hotel in Chennai vs Scraper verified hotel in Puducherry.
    User searches 'hotel' + 'Puducherry'.
    Puducherry hotel MUST appear; Chennai hotel MUST NOT appear.
    """
    db = SessionLocal()
    try:
        chennai_hotel = Organization(
            name="Hotel Chennai Admin",
            category="HOTEL",
            country="India",
            state="Tamil Nadu",
            district="Chennai",
            city="Chennai",
            admin_verified=True,
            confidence="HIGH"
        )
        puducherry_hotel = Organization(
            name="Hotel Puducherry Scraper",
            category="HOTEL",
            country="India",
            state="Puducherry",
            district="Puducherry",
            city="Puducherry",
            admin_verified=False,
            identity_verified=True,
            category_verified=True,
            country_verified=True,
            state_verified=True,
            district_verified=True,
            location_verified=True,
            official_website_verified=True,
            confidence="HIGH"
        )
        db.add_all([chennai_hotel, puducherry_hotel])
        db.commit()
    finally:
        db.close()

    headers = get_user_headers("user_instant@leaddiscovery.com")
    res = client.post("/api/tasks/scrape", json={"keyword": "hotel", "location": "Puducherry", "max_results": 15}, headers=headers)
    assert res.status_code == 201
    data = res.json()

    found_names = [o["name"] for o in data.get("fast_verified_results", [])]
    assert "Hotel Puducherry Scraper" in found_names
    assert "Hotel Chennai Admin" not in found_names

def test_category_priority_in_task_creation():
    """
    Requirement 30:
    Admin verified hotel in Puducherry vs Admin verified school in Puducherry.
    User searches 'hotel' + 'Puducherry'.
    Only Hotel Puducherry appears; School Puducherry is excluded.
    """
    db = SessionLocal()
    try:
        hotel = Organization(
            name="Puducherry Heritage Hotel",
            category="HOTEL",
            country="India",
            state="Puducherry",
            district="Puducherry",
            city="Puducherry",
            admin_verified=True
        )
        school = Organization(
            name="Puducherry High School",
            category="SCHOOL",
            country="India",
            state="Puducherry",
            district="Puducherry",
            city="Puducherry",
            admin_verified=True
        )
        db.add_all([hotel, school])
        db.commit()
    finally:
        db.close()

    headers = get_user_headers("user_instant@leaddiscovery.com")
    res = client.post("/api/tasks/scrape", json={"keyword": "hotel", "location": "Puducherry", "max_results": 15}, headers=headers)
    assert res.status_code == 201
    data = res.json()

    found_names = [o["name"] for o in data.get("fast_verified_results", [])]
    assert "Puducherry Heritage Hotel" in found_names
    assert "Puducherry High School" not in found_names

def test_quarantine_exclusion_in_task_creation():
    """
    Requirement 31:
    Quarantined organization matching category & location MUST be excluded.
    """
    db = SessionLocal()
    try:
        quarantined = Organization(
            name="Fake Puducherry Hotel",
            category="HOTEL",
            country="India",
            state="Puducherry",
            district="Puducherry",
            city="Puducherry",
            admin_verified=False,
            is_quarantined=True,
            quarantine_reason="Spam site"
        )
        db.add(quarantined)
        db.commit()
    finally:
        db.close()

    headers = get_user_headers("user_instant@leaddiscovery.com")
    res = client.post("/api/tasks/scrape", json={"keyword": "hotel", "location": "Puducherry", "max_results": 15}, headers=headers)
    assert res.status_code == 201
    data = res.json()

    found_names = [o["name"] for o in data.get("fast_verified_results", [])]
    assert "Fake Puducherry Hotel" not in found_names
