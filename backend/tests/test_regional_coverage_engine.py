import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.models import User, ScrapingTask, Organization, Website, District
from app.core.tn_districts import TAMIL_NADU_DISTRICTS, ALL_REGIONS, seed_tn_districts, normalize_district
from app.api.organizations import get_campaign_matrix, _query_eligible_matrix_counts
from app.api.admin import get_admin_overview
from app.api.campaigns import resolve_target_bound
from app.services.location_service import verify_organization_location
from app.services.scraper.identification import identify_official_website

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    seed_tn_districts(session)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

def test_01_all_38_tn_districts_exist(db: Session):
    tn_names = [d["name"] for d in TAMIL_NADU_DISTRICTS]
    assert len(tn_names) == 38
    for d_name in tn_names:
        dist_record = db.query(District).filter(District.district_name == d_name).first()
        assert dist_record is not None
        assert dist_record.state == "Tamil Nadu"

def test_02_exactly_1_puducherry_ut_row(db: Session):
    assert len(ALL_REGIONS) == 39
    py_rows = [r for r in ALL_REGIONS if r["name"] == "Puducherry"]
    assert len(py_rows) == 1
    assert py_rows[0]["state"] == "Puducherry UT"

def test_03_no_kancheepuram_kanchipuram_duplicate(db: Session):
    assert normalize_district("Kanchipuram") == "Kancheepuram"
    assert normalize_district("Kancheepuram") == "Kancheepuram"
    assert normalize_district("kanchipuram") == "Kancheepuram"
    assert normalize_district("Pondicherry") == "Puducherry"
    assert normalize_district("Karaikal") == "Puducherry"

def test_04_puducherry_not_classified_as_tamil_nadu(db: Session):
    py_record = db.query(District).filter(District.district_name == "Puducherry").first()
    assert py_record.state == "Puducherry UT"
    assert py_record.state != "Tamil Nadu"

def test_05_strict_district_matching(db: Session):
    admin_user = User(email="testadmin@test.com", role="ADMIN", status="ACTIVE")
    matrix_before = get_campaign_matrix(db=db, admin_user=admin_user)
    salem_hotels_before = next((r["hotels"] for r in matrix_before if r["region"].lower() == "salem"), 0)
    chennai_hotels_before = next((r["hotels"] for r in matrix_before if r["region"].lower() == "chennai"), 0)

    chennai_org = Organization(
        name="Chennai Central Hotel Unique", category="Hotel", district="Chennai",
        state="Tamil Nadu", country="India", source_type="SCRAPER_VERIFIED",
        admin_verified=False, is_quarantined=False, official_website_verified=True
    )
    db.add(chennai_org)
    db.commit()
    matrix_after = get_campaign_matrix(db=db, admin_user=admin_user)
    salem_row = next((r for r in matrix_after if r["region"].lower() == "salem"), None)
    chennai_row = next((r for r in matrix_after if r["region"].lower() == "chennai"), None)
    assert salem_row["hotels"] == salem_hotels_before
    assert chennai_row["hotels"] >= chennai_hotels_before + 1

def test_06_strict_country_matching():
    valid, reason, meta = verify_organization_location("Chennai", "US Tech Inc", detected_address="New York, USA", domain="ustech.us")
    assert not valid
    assert "COUNTRY_MISMATCH" in reason

def test_07_strict_category_matching(db: Session):
    admin_user = User(email="testadmin@test.com", role="ADMIN", status="ACTIVE")
    matrix_before = get_campaign_matrix(db=db, admin_user=admin_user)
    cbe_hotels_before = next((r["hotels"] for r in matrix_before if r["region"].lower() == "coimbatore"), 0)
    cbe_it_before = next((r["it_companies"] for r in matrix_before if r["region"].lower() == "coimbatore"), 0)

    it_org = Organization(
        name="Coimbatore Software Solutions Unique", category="IT Company", district="Coimbatore",
        state="Tamil Nadu", country="India", source_type="SCRAPER_VERIFIED",
        admin_verified=False, is_quarantined=False, official_website_verified=True
    )
    db.add(it_org)
    db.commit()
    matrix_after = get_campaign_matrix(db=db, admin_user=admin_user)
    cbe_row = next((r for r in matrix_after if r["region"].lower() == "coimbatore"), None)
    assert cbe_row["it_companies"] >= cbe_it_before + 1
    assert cbe_row["hotels"] == cbe_hotels_before

def test_08_quarantined_records_excluded(db: Session):
    admin_user = User(email="testadmin@test.com", role="ADMIN", status="ACTIVE")
    matrix_before = get_campaign_matrix(db=db, admin_user=admin_user)
    salem_hotels_before = next((r["hotels"] for r in matrix_before if r["region"].lower() == "salem"), 0)

    q_org = Organization(
        name="Quarantined Hotel Salem Unique", category="Hotel", district="Salem",
        state="Tamil Nadu", country="India", source_type="UNVERIFIED",
        admin_verified=False, is_quarantined=True, quarantine_reason="Unverified website"
    )
    db.add(q_org)
    db.commit()
    matrix_after = get_campaign_matrix(db=db, admin_user=admin_user)
    salem_row = next((r for r in matrix_after if r["region"].lower() == "salem"), None)
    assert salem_row["hotels"] == salem_hotels_before

def test_09_raw_candidates_excluded(db: Session):
    admin_user = User(email="testadmin@test.com", role="ADMIN", status="ACTIVE")
    matrix_before = get_campaign_matrix(db=db, admin_user=admin_user)
    salem_hotels_before = next((r["hotels"] for r in matrix_before if r["region"].lower() == "salem"), 0)

    raw_org = Organization(
        name="Unverified Raw Candidate Unique", category="Hotel", district="Salem",
        state="Tamil Nadu", country="India", source_type="AUTOMATIC",
        admin_verified=False, is_quarantined=False
    )
    db.add(raw_org)
    db.commit()
    matrix_after = get_campaign_matrix(db=db, admin_user=admin_user)
    salem_row = next((r for r in matrix_after if r["region"].lower() == "salem"), None)
    assert salem_row["hotels"] == salem_hotels_before

def test_10_directory_only_records_excluded():
    eval_res = identify_official_website("Salem Grand Hotel", "https://www.justdial.com/Salem/Salem-Grand-Hotel")
    assert eval_res["is_directory_source"] == True
    assert eval_res["is_official"] == False

def test_11_target_bounds_resolution():
    assert resolve_target_bound("Hotels") == 50
    assert resolve_target_bound("Hospitals") == 20
    assert resolve_target_bound("Schools") == 23
    assert resolve_target_bound("Colleges") == 32
    assert resolve_target_bound("Companies") == 24
    assert resolve_target_bound("IT Companies") == 28

def test_12_matrix_parity_with_postgresql(db: Session):
    admin_user = User(email="testadmin@test.com", role="ADMIN", status="ACTIVE")
    matrix = get_campaign_matrix(db=db, admin_user=admin_user)
    counts_map = _query_eligible_matrix_counts(db)
    for row in matrix:
        reg_name = row["region"]
        c = counts_map.get(reg_name.lower(), {"total": 0})
        assert row["total"] == c["total"]

def test_13_admin_overview_functional(db: Session):
    admin_user = User(email="testadmin@test.com", role="ADMIN", status="ACTIVE")
    overview = get_admin_overview(db=db, admin_user=admin_user)
    assert "total_users" in overview
    assert "total_tasks" in overview
    assert "total_leads" in overview
