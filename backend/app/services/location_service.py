import re
from typing import Dict, Any, Tuple, Set, Optional

# Administrative Districts of Tamil Nadu & Union Territory of Puducherry
TN_DISTRICTS_DATA = {
    "erode": {
        "district": "Erode",
        "state": "Tamil Nadu",
        "cities_towns": {"erode", "bhavani", "gobichettipalayam", "gobi", "sathyamangalam", "sathy", "perundurai", "anthiyur", "kodumudi", "modakkurichi", "chennimalai", "nambiyur", "thalavadi", "kalingarayanpalayam"}
    },
    "kanyakumari": {
        "district": "Kanyakumari",
        "state": "Tamil Nadu",
        "cities_towns": {"kanyakumari", "nagercoil", "thuckalay", "marthandam", "colachel", "padmanabhapuram", "karungal", "kuzhithurai", "agastheeswaram"}
    },
    "salem": {
        "district": "Salem",
        "state": "Tamil Nadu",
        "cities_towns": {"salem", "mettur", "omalur", "attur", "sankari", "yercaud", "edappadi", "valapady"}
    },
    "coimbatore": {
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "cities_towns": {"coimbatore", "pollachi", "metupalayam", "sulur", "annur", "kinathukadavu", "valparai"}
    },
    "chennai": {
        "district": "Chennai",
        "state": "Tamil Nadu",
        "cities_towns": {"chennai", "madras", "gopalapuram", "adyar", "anna nagar", "t nagar", "velachery", "tambaram", "guindy", "chromepet", "porur"}
    },
    "tiruchirappalli": {
        "district": "Tiruchirappalli",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruchirappalli", "trichy", "srirangam", "lalgudi", "manapparai", "thottiyam", "musiri"}
    },
    "madurai": {
        "district": "Madurai",
        "state": "Tamil Nadu",
        "cities_towns": {"madurai", "melur", "thirumangalam", "usilampatti", "vadipatti", "sholavandan"}
    },
    "tiruppur": {
        "district": "Tiruppur",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruppur", "tirupur", "avanashi", "udumalaipettai", "udumalpet", "dharapuram", "kangeyam", "palladam"}
    },
    "vellore": {
        "district": "Vellore",
        "state": "Tamil Nadu",
        "cities_towns": {"vellore", "katpadi", "gudiyatham", "anaicut", "pernamallur"}
    },
    "thanjavur": {
        "district": "Thanjavur",
        "state": "Tamil Nadu",
        "cities_towns": {"thanjavur", "kumbakonam", "pattukkottai", "orathanadu", "thiruvaiyaru"}
    },
    "dindigul": {
        "district": "Dindigul",
        "state": "Tamil Nadu",
        "cities_towns": {"dindigul", "kodaikanal", "palani", "oddanchatram", "neduvasal"}
    },
    "tirunelveli": {
        "district": "Tirunelveli",
        "state": "Tamil Nadu",
        "cities_towns": {"tirunelveli", "palayamkottai", "nanguneri", "radhapuram", "ambasamudram"}
    },
    "karur": {
        "district": "Karur",
        "state": "Tamil Nadu",
        "cities_towns": {"karur", "kulithalai", "aravakurichi", "krishnarayapuram"}
    },
    "namakkal": {
        "district": "Namakkal",
        "state": "Tamil Nadu",
        "cities_towns": {"namakkal", "rasipuram", "tiruchengodu", "paramathi velur"}
    },
    "cuddalore": {
        "district": "Cuddalore",
        "state": "Tamil Nadu",
        "cities_towns": {"cuddalore", "chidambaram", "panruti", "virudhachalam", "neiveli"}
    },
    "puducherry": {
        "district": "Puducherry",
        "state": "Puducherry UT",
        "cities_towns": {"puducherry", "pondicherry", "pondy", "ouzhangarai", "moolakulam", "lawspet", "kalapet", "karaikal", "mahe", "yanam"}
    }
}

# Cross-district lookup map (City/Town -> District Name)
ALL_INDIAN_CITIES_DISTRICT_MAP = {}
for dist_key, data in TN_DISTRICTS_DATA.items():
    dist_name = data["district"]
    for c in data["cities_towns"]:
        ALL_INDIAN_CITIES_DISTRICT_MAP[c] = dist_name

# Add other major Indian cities to cross-district detection map
OTHER_MAJOR_CITIES = {
    "mumbai": "Mumbai", "delhi": "Delhi", "bangalore": "Bengaluru", "bengaluru": "Bengaluru",
    "hyderabad": "Hyderabad", "kolkata": "Kolkata", "pune": "Pune", "ahmedabad": "Ahmedabad",
    "surat": "Surat", "jaipur": "Jaipur", "lucknow": "Lucknow", "kanpur": "Kanpur",
    "nagpur": "Nagpur", "indore": "Indore", "thane": "Thane", "bhopal": "Bhopal",
    "visakhapatnam": "Visakhapatnam", "vizag": "Visakhapatnam", "patna": "Patna",
    "vadodara": "Vadodara", "ghaziabad": "Ghaziabad", "ludhiana": "Ludhiana",
    "agra": "Agra", "nashik": "Nashik", "faridabad": "Faridabad", "meerut": "Meerut",
    "rajkot": "Rajkot", "varanasi": "Varanasi", "coimbatore": "Coimbatore",
    "vijayawada": "Vijayawada", "jodhpur": "Jodhpur", "madurai": "Madurai",
    "raipur": "Raipur", "kota": "Kota", "guwahati": "Guwahati", "chandigarh": "Chandigarh",
    "mysore": "Mysore", "gurgaon": "Gurugram", "gurugram": "Gurugram", "noida": "Noida",
    "kochi": "Kochi", "cochin": "Kochi", "thiruvananthapuram": "Thiruvananthapuram", "trivandrum": "Thiruvananthapuram"
}
for c, d in OTHER_MAJOR_CITIES.items():
    if c not in ALL_INDIAN_CITIES_DISTRICT_MAP:
        ALL_INDIAN_CITIES_DISTRICT_MAP[c] = d


def normalize_target_location(location_str: str) -> Dict[str, Any]:
    """
    Normalizes user-specified location string into structured target components:
    target_country, target_state_or_ut, target_district, target_city, valid_cities_in_district.
    """
    if not location_str:
        return {
            "target_country": "India",
            "target_state_or_ut": "Tamil Nadu",
            "target_district": "",
            "target_city": "",
            "valid_cities_in_district": set(),
            "raw_input": location_str
        }

    loc_low = location_str.lower().strip()
    
    # Handle Puducherry UT specifically
    if any(p in loc_low for p in ["puducherry", "pondicherry", "pondy", "karaikal", "mahe", "yanam"]):
        return {
            "target_country": "India",
            "target_state_or_ut": "Puducherry UT",
            "target_district": "Puducherry",
            "target_city": "Puducherry",
            "valid_cities_in_district": {"puducherry", "pondicherry", "pondy", "karaikal", "mahe", "yanam", "ouzhangarai", "moolakulam", "lawspet", "kalapet"},
            "raw_input": location_str
        }

    # Match district in TN_DISTRICTS_DATA
    for dist_key, data in TN_DISTRICTS_DATA.items():
        if dist_key in loc_low or data["district"].lower() in loc_low or any(c in loc_low for c in data["cities_towns"]):
            return {
                "target_country": "India",
                "target_state_or_ut": data["state"],
                "target_district": data["district"],
                "target_city": data["district"],
                "valid_cities_in_district": set(data["cities_towns"]),
                "raw_input": location_str
            }

    # Generic extraction for other locations
    tokens = [t for t in loc_low.split() if t not in ("in", "the", "and", "near", "district", "city", "ut", "state", "india")]
    district_name = tokens[0].capitalize() if tokens else loc_low.capitalize()
    
    return {
        "target_country": "India",
        "target_state_or_ut": "Tamil Nadu",
        "target_district": district_name,
        "target_city": district_name,
        "valid_cities_in_district": set(tokens),
        "raw_input": location_str
    }


def verify_organization_location(
    target_location_str: str,
    org_name: str,
    detected_address: str = "",
    html_text: str = "",
    domain: str = ""
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Generic Location Matching & Verification Engine.
    Validates physical location evidence against requested target location.
    Enforces EXACT DISTRICT PROTECTION and STRICT COUNTRY/STATE/UT SEPARATION.
    
    Returns:
        (is_location_valid: bool, reason: str, metadata: dict)
    """
    target = normalize_target_location(target_location_str)
    
    metadata = {
        "country_verified": False,
        "state_verified": False,
        "district_verified": False,
        "city_verified": False,
        "location_verified": False,
        "detected_district": None,
        "rejection_reason": None
    }

    if not target_location_str or not target_location_str.strip():
        metadata.update({"country_verified": True, "state_verified": True, "district_verified": True, "city_verified": True, "location_verified": True})
        return True, "PASS", metadata

    combined_text = f"{org_name} {detected_address} {html_text[:2000]}".lower().replace("-", " ").replace("_", " ")
    domain_low = (domain or "").lower().strip()

    # 1. COUNTRY VERIFICATION & PROTECTION
    if target["target_country"] == "India":
        foreign_tlds = [".jp", ".cn", ".uk", ".au", ".ca", ".de", ".fr", ".sg", ".my", ".ae", ".tw", ".mo", ".kr", ".ru", ".br", ".us"]
        for tld in foreign_tlds:
            if domain_low.endswith(tld):
                if not any(in_tok in combined_text for in_tok in ["india", "puducherry", "pondicherry", "tamil nadu", target["target_district"].lower()]):
                    metadata["rejection_reason"] = "COUNTRY_MISMATCH"
                    return False, "COUNTRY_MISMATCH (Foreign domain TLD)", metadata

        foreign_countries = ["united states", "usa", "uk", "united kingdom", "canada", "australia", "germany", "france", "singapore", "malaysia", "uae", "dubai", "qatar", "japan", "china"]
        for fc in foreign_countries:
            if re.search(rf'\b{re.escape(fc)}\b', combined_text):
                if not any(in_tok in combined_text for in_tok in ["india", "puducherry", "pondicherry", "tamil nadu", target["target_district"].lower()]):
                    metadata["rejection_reason"] = "COUNTRY_MISMATCH"
                    return False, f"COUNTRY_MISMATCH (Foreign country '{fc}' detected)", metadata

    metadata["country_verified"] = True

    # 2. STATE / UNION TERRITORY PROTECTION
    if target["target_state_or_ut"] == "Puducherry UT":
        # Must not belong to Tamil Nadu, Kerala, or AP unless explicitly matching Puducherry region
        if any(tn_city in combined_text for tn_city in ["chennai", "coimbatore", "madurai", "salem", "erode", "kanyakumari", "nagercoil", "trichy"]):
            if not any(p_city in combined_text for p_city in target["valid_cities_in_district"]):
                metadata["rejection_reason"] = "STATE_MISMATCH"
                return False, "STATE_MISMATCH (Tamil Nadu city detected for Puducherry UT target)", metadata
    metadata["state_verified"] = True

    # 3. INTER-DISTRICT CONFLICT CHECK (EXACT DISTRICT PROTECTION)
    target_dist_low = target["target_district"].lower()
    valid_cities = target["valid_cities_in_district"]

    for city_key, dist_val in ALL_INDIAN_CITIES_DISTRICT_MAP.items():
        if city_key not in valid_cities and len(city_key) >= 4:
            pattern = rf'\b{re.escape(city_key)}\b'
            if re.search(pattern, combined_text):
                # Check if target city is also explicitly present
                has_target_city = any(re.search(rf'\b{re.escape(tc)}\b', combined_text) for tc in valid_cities if len(tc) >= 3)
                if not has_target_city:
                    metadata["detected_district"] = dist_val
                    metadata["rejection_reason"] = "DISTRICT_MISMATCH"
                    return False, f"DISTRICT_MISMATCH (Candidate is in '{dist_val}' ['{city_key}'], target is '{target['target_district']}')", metadata

    # 4. VERIFY TARGET LOCATION EVIDENCE PRESENCE
    has_target_evidence = any(re.search(rf'\b{re.escape(tc)}\b', combined_text) for tc in valid_cities if len(tc) >= 3)
    if not has_target_evidence and domain_low:
        has_target_evidence = any(tc in domain_low for tc in valid_cities if len(tc) >= 4)

    if not has_target_evidence:
        metadata["rejection_reason"] = "LOCATION_UNVERIFIED"
        return False, f"LOCATION_UNVERIFIED (Target location '{target_location_str}' not verified in candidate address/content)", metadata

    metadata["district_verified"] = True
    metadata["city_verified"] = True
    metadata["location_verified"] = True

    return True, "PASS", metadata
