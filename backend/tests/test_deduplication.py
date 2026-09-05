from app.services.deduplication import calculate_match_score, merge_organizations, deduplicate_leads

def test_calculate_match_score():
    # Domain match
    org1 = {"name": "ABC School", "domain": "abcschool.org", "emails": [], "phones": []}
    org2 = {"name": "ABC International School", "domain": "abcschool.org", "emails": [], "phones": []}
    assert calculate_match_score(org1, org2) == 1.0
    
    # Email match
    org3 = {"name": "ABC School", "domain": "abc.com", "emails": [{"email": "info@abc.com"}], "phones": []}
    org4 = {"name": "XYZ Academy", "domain": "xyz.com", "emails": [{"email": "info@abc.com"}], "phones": []}
    assert calculate_match_score(org3, org4) == 0.95
    
    # Phone match
    org5 = {"name": "ABC School", "domain": "", "emails": [], "phones": [{"normalized_value": "+919876543210"}]}
    org6 = {"name": "XYZ Academy", "domain": "", "emails": [], "phones": [{"normalized_value": "+919876543210"}]}
    assert calculate_match_score(org5, org6) == 0.90
    
    # Jaccard name matching
    org7 = {"name": "Delhi Public School Puducherry", "domain": "", "emails": [], "phones": [], "city": "Puducherry"}
    org8 = {"name": "Delhi Public School", "domain": "", "emails": [], "phones": [], "city": "Puducherry"}
    score = calculate_match_score(org7, org8)
    assert score >= 0.8  # Expect high Jaccard due to name overlap and same city

def test_merge_organizations():
    org1 = {
        "name": "Delhi Public School",
        "category": "CBSE Schools",
        "address": "12 Beach Road",
        "city": "Puducherry",
        "state": "Puducherry",
        "pincode": "605001",
        "domain": "dps.org",
        "possible_website": "https://dps.org",
        "source_url": "https://duckduckgo.com/dps",
        "discovery_source": "DuckDuckGo",
        "emails": [{"email": "info@dps.org", "source_url": "https://dps.org/contact", "extraction_method": "mailto"}],
        "phones": [{"raw_value": "9876543210", "normalized_value": "+919876543210", "type": "main", "source_url": "https://dps.org"}],
        "socials": [{"platform": "facebook", "url": "https://facebook.com/dps", "source_url": "https://dps.org"}],
        "people": [],
        "confidence": "MEDIUM"
    }
    
    org2 = {
        "name": "Delhi Public School Puducherry Branch",
        "category": "CBSE Schools",
        "address": "12 Beach Road, Puducherry, India",
        "city": "Puducherry",
        "state": "Puducherry",
        "pincode": "605001",
        "domain": "dps.org",
        "possible_website": "https://dps.org",
        "source_url": "https://duckduckgo.com/dps-puducherry",
        "discovery_source": "DuckDuckGo",
        "emails": [{"email": "admissions@dps.org", "source_url": "https://dps.org/admissions", "extraction_method": "regex"}],
        "phones": [{"raw_value": "9876543210", "normalized_value": "+919876543210", "type": "admissions", "source_url": "https://dps.org/admissions"}],
        "socials": [],
        "people": [{"name": "Dr. Kumar", "designation": "Principal"}],
        "confidence": "HIGH"
    }
    
    merged = merge_organizations(org1, org2)
    
    # Name should be the longer one
    assert merged["name"] == "Delhi Public School Puducherry Branch"
    # Address should be the longer one
    assert merged["address"] == "12 Beach Road, Puducherry, India"
    # Emails should be combined
    emails = {e["email"] for e in merged["emails"]}
    assert "info@dps.org" in emails
    assert "admissions@dps.org" in emails
    # Phones should be deduplicated (only one unique normalized phone number)
    assert len(merged["phones"]) == 1
    # People should be included
    assert len(merged["people"]) == 1
    # Confidence should be the highest (HIGH)
    assert merged["confidence"] == "HIGH"

def test_deduplicate_leads():
    leads = [
        {"name": "School A", "domain": "schoola.com", "emails": [], "phones": []},
        {"name": "School B", "domain": "schoolb.com", "emails": [], "phones": []},
        {"name": "School A Branch", "domain": "schoola.com", "emails": [], "phones": []}
    ]
    deduped = deduplicate_leads(leads)
    assert len(deduped) == 2
    names = {l["name"] for l in deduped}
    assert "School A Branch" in names  # Longer name matches from merged
    assert "School B" in names
