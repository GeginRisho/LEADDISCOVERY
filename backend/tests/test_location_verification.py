import pytest
from app.services.verification import is_location_matching

def test_puducherry_vs_andhra_pradesh_rejection():
    # Test case 1: Target = Puducherry, Candidate = Aditya Educational Institutions in Andhra Pradesh
    is_valid, reason = is_location_matching(
        requested_location="Puducherry",
        org_name="Aditya Educational Institutions",
        detected_address="Surampalem, Kakinada, East Godavari District, Andhra Pradesh 533437",
        html_text="Aditya Educational Institutions, Andhra Pradesh, India",
        domain="aditya.ac.in"
    )
    assert not is_valid
    assert any(code in reason for code in ["LOCATION_MISMATCH", "LOCATION_UNVERIFIED", "STATE_MISMATCH", "DISTRICT_MISMATCH"])

def test_puducherry_vs_foreign_country_rejection():
    # Test case 2: Target = Puducherry, Candidate = Organization in USA/UK
    is_valid, reason = is_location_matching(
        requested_location="Puducherry",
        org_name="JMJ Global Corporation",
        detected_address="123 Main Street, New York, NY 10001, USA",
        html_text="JMJ USA Headquarters, New York",
        domain="jmj.com"
    )
    assert not is_valid
    assert any(code in reason for code in ["COUNTRY_MISMATCH", "LOCATION_MISMATCH", "LOCATION_UNVERIFIED"])

def test_puducherry_legitimate_school_pass():
    # Test case 3: Target = Puducherry, Candidate = Petit Seminaire CBSE School in Puducherry
    is_valid, reason = is_location_matching(
        requested_location="Puducherry",
        org_name="Petit Seminaire CBSE School",
        detected_address="Moolakulam, Puducherry 605010, Puducherry UT, India",
        html_text="Petit Seminaire CBSE School Moolakulam Puducherry",
        domain="petitcbse.com"
    )
    assert is_valid
    assert reason == "PASS"

def test_kanyakumari_vs_chennai_rejection():
    # Test case 4: Target = Kanyakumari, Candidate = School in Chennai
    is_valid, reason = is_location_matching(
        requested_location="Kanyakumari",
        org_name="DAV Boys Senior Secondary School",
        detected_address="Gopalapuram, Chennai, Tamil Nadu 600086",
        html_text="DAV Boys School Gopalapuram Chennai",
        domain="davchennai.org"
    )
    assert not is_valid
    assert any(code in reason for code in ["LOCATION_MISMATCH", "DISTRICT_MISMATCH"])

def test_salem_vs_coimbatore_rejection():
    # Test case 5: Target = Salem, Candidate = Hospital in Coimbatore
    is_valid, reason = is_location_matching(
        requested_location="Salem",
        org_name="Kovai Medical Center and Hospital",
        detected_address="Avinashi Road, Coimbatore, Tamil Nadu 641014",
        html_text="KMCH Hospital Coimbatore Tamil Nadu",
        domain="kmchhospitals.com"
    )
    assert not is_valid
    assert any(code in reason for code in ["LOCATION_MISMATCH", "DISTRICT_MISMATCH"])
