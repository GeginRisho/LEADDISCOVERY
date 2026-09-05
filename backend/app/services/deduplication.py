import re
from typing import List, Dict, Any
from app.services.scraper.identification import clean_org_name
from app.services.cleaning import clean_lead_data

def calculate_match_score(org1: Dict[str, Any], org2: Dict[str, Any]) -> float:
    """
    Calculates a similarity score between 0.0 and 1.0.
    """
    from app.services.scraper.identification import is_directory_domain
    
    # 1. Domain match check (highest indicator of duplicate, but NOT for directory portal domains)
    dom1 = org1.get("domain")
    dom2 = org2.get("domain")
    if dom1 and dom2 and dom1 == dom2 and not is_directory_domain(dom1):
        return 1.0

    # 2. Email match check
    emails1 = {e["email"].lower().strip() for e in org1.get("emails", [])}
    emails2 = {e["email"].lower().strip() for e in org2.get("emails", [])}
    if emails1 and emails2 and emails1.intersection(emails2):
        return 0.95

    # 3. Phone match check
    phones1 = {p["normalized_value"].strip() for p in org1.get("phones", [])}
    phones2 = {p["normalized_value"].strip() for p in org2.get("phones", [])}
    if phones1 and phones2 and phones1.intersection(phones2):
        return 0.90

    # 4. Name similarity check with location context
    name1 = clean_org_name(org1["name"])
    name2 = clean_org_name(org2["name"])
    if not name1 or not name2:
        return 0.0

    words1 = set(name1.split())
    words2 = set(name2.split())
    if not words1 or not words2:
        return 0.0

    # Calculate Jaccard similarity of name words
    jaccard = len(words1.intersection(words2)) / len(words1.union(words2))

    if jaccard >= 0.6:
        # Boost if in the same city
        city1 = (org1.get("city") or "").lower().strip()
        city2 = (org2.get("city") or "").lower().strip()
        if city1 and city2 and city1 == city2:
            return 0.85
        return jaccard

    return jaccard

def merge_organizations(org1: Dict[str, Any], org2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges two organization dicts, preserving the best and unique records.
    """
    merged = {}
    
    # 1. Use the longer name (often more descriptive)
    name1 = org1.get("name", "")
    name2 = org2.get("name", "")
    merged["name"] = name1 if len(name1) >= len(name2) else name2
    
    merged["category"] = org1.get("category") or org2.get("category")
    
    # 2. Merge address details, prioritizing the longer/more complete ones
    addr1 = org1.get("address", "")
    addr2 = org2.get("address", "")
    merged["address"] = addr1 if len(addr1) >= len(addr2) else addr2
    
    merged["city"] = org1.get("city") or org2.get("city")
    merged["state"] = org1.get("state") or org2.get("state")
    merged["pincode"] = org1.get("pincode") or org2.get("pincode")
    
    # Domain & URL
    merged["domain"] = org1.get("domain") or org2.get("domain")
    merged["possible_website"] = org1.get("possible_website") or org2.get("possible_website")
    merged["source_url"] = org1.get("source_url") or org2.get("source_url")
    merged["discovery_source"] = org1.get("discovery_source") or org2.get("discovery_source")
    
    # 3. Combine contact lists
    merged["emails"] = org1.get("emails", []) + org2.get("emails", [])
    merged["phones"] = org1.get("phones", []) + org2.get("phones", [])
    merged["socials"] = org1.get("socials", []) + org2.get("socials", [])
    merged["people"] = org1.get("people", []) + org2.get("people", [])
    
    # 4. Run standard cleaning to remove duplicates inside combined lists
    merged = clean_lead_data(merged)
    
    # 5. Take highest confidence
    conf1 = org1.get("confidence", "LOW")
    conf2 = org2.get("confidence", "LOW")
    
    order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    if order.get(conf1, 0) >= order.get(conf2, 0):
        merged["confidence"] = conf1
    else:
        merged["confidence"] = conf2
        
    return merged

def deduplicate_leads(leads: List[Dict[str, Any]], threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Groups and merges duplicate leads from a list of discovered organizations.
    """
    if not leads:
        return []
        
    unique_leads: List[Dict[str, Any]] = []
    
    for lead in leads:
        matched_idx = -1
        highest_score = 0.0
        
        # Check against existing unique leads
        for idx, u_lead in enumerate(unique_leads):
            score = calculate_match_score(lead, u_lead)
            if score >= threshold and score > highest_score:
                matched_idx = idx
                highest_score = score
                
        if matched_idx != -1:
            # Merge with existing lead
            unique_leads[matched_idx] = merge_organizations(unique_leads[matched_idx], lead)
        else:
            # Append as new unique lead
            unique_leads.append(clean_lead_data(lead))
            
    return unique_leads
