import re
from typing import Dict, Any, Tuple, Set, Optional
from app.core.tn_districts import normalize_district

# Administrative Districts of Tamil Nadu (All 38 Districts) & Union Territory of Puducherry
TN_DISTRICTS_DATA = {
    "ariyalur": {
        "district": "Ariyalur",
        "state": "Tamil Nadu",
        "cities_towns": {"ariyalur", "jayankondam", "sendurai", "andimadam"}
    },
    "chengalpattu": {
        "district": "Chengalpattu",
        "state": "Tamil Nadu",
        "cities_towns": {"chengalpattu", "kancheepuram", "chromepet", "pallavaram", "tambaram", "vandalur", "guduvancheri", "chengalpet", "maduranthakam", "cheyyur", "mamallapuram", "mahabalipuram"}
    },
    "chennai": {
        "district": "Chennai",
        "state": "Tamil Nadu",
        "cities_towns": {"chennai", "madras", "gopalapuram", "adyar", "anna nagar", "t nagar", "velachery", "tambaram", "guindy", "chromepet", "porur", "royapettah", "mylapore", "egmore", "kilpauk", "perambur", "tnagar"}
    },
    "coimbatore": {
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "cities_towns": {"coimbatore", "pollachi", "metupalayam", "mettupalayam", "sulur", "annur", "kinathukadavu", "valparai"}
    },
    "cuddalore": {
        "district": "Cuddalore",
        "state": "Tamil Nadu",
        "cities_towns": {"cuddalore", "chidambaram", "panruti", "virudhachalam", "neiveli", "neyveli", "kattumannarkoil", "bhuvanagiri"}
    },
    "dharmapuri": {
        "district": "Dharmapuri",
        "state": "Tamil Nadu",
        "cities_towns": {"dharmapuri", "harur", "palacode", "pennagaram", "pappireddipatti"}
    },
    "dindigul": {
        "district": "Dindigul",
        "state": "Tamil Nadu",
        "cities_towns": {"dindigul", "kodaikanal", "palani", "oddanchatram", "neduvasal", "natham", "nakkal", "nilakottai"}
    },
    "erode": {
        "district": "Erode",
        "state": "Tamil Nadu",
        "cities_towns": {"erode", "bhavani", "gobichettipalayam", "gobi", "sathyamangalam", "sathy", "perundurai", "anthiyur", "kodumudi", "modakkurichi", "chennimalai", "nambiyur", "thalavadi", "kalingarayanpalayam"}
    },
    "kallakurichi": {
        "district": "Kallakurichi",
        "state": "Tamil Nadu",
        "cities_towns": {"kallakurichi", "sankarapuram", "chinhasalem", "chinnasalem", "ulundurpet", "tirukoilur"}
    },
    "kancheepuram": {
        "district": "Kancheepuram",
        "state": "Tamil Nadu",
        "cities_towns": {"kanchipuram", "kancheepuram", "sriperumbudur", "walajabad", "uttiramerur"}
    },
    "kanyakumari": {
        "district": "Kanyakumari",
        "state": "Tamil Nadu",
        "cities_towns": {"kanyakumari", "kanniyakumari", "nagercoil", "thuckalay", "marthandam", "colachel", "padmanabhapuram", "karungal", "kuzhithurai", "agastheeswaram"}
    },
    "karur": {
        "district": "Karur",
        "state": "Tamil Nadu",
        "cities_towns": {"karur", "kulithalai", "aravakurichi", "krishnarayapuram"}
    },
    "krishnagiri": {
        "district": "Krishnagiri",
        "state": "Tamil Nadu",
        "cities_towns": {"krishnagiri", "hosur", "denkanikottai", "pochampalli", "bargur", "uthangarai"}
    },
    "madurai": {
        "district": "Madurai",
        "state": "Tamil Nadu",
        "cities_towns": {"madurai", "melur", "thirumangalam", "usilampatti", "vadipatti", "sholavandan"}
    },
    "mayiladuthurai": {
        "district": "Mayiladuthurai",
        "state": "Tamil Nadu",
        "cities_towns": {"mayiladuthurai", "sirkali", "tharangambadi", "kuthalam"}
    },
    "nagapattinam": {
        "district": "Nagapattinam",
        "state": "Tamil Nadu",
        "cities_towns": {"nagapattinam", "velankanni", "kilvelur", "vedaranyam"}
    },
    "namakkal": {
        "district": "Namakkal",
        "state": "Tamil Nadu",
        "cities_towns": {"namakkal", "rasipuram", "tiruchengodu", "paramathi velur", "komarapalayam"}
    },
    "nilgiris": {
        "district": "Nilgiris",
        "state": "Tamil Nadu",
        "cities_towns": {"ooty", "udhagamandalam", "coonoor", "gudalur", "kotagiri", "kundah"}
    },
    "perambalur": {
        "district": "Perambalur",
        "state": "Tamil Nadu",
        "cities_towns": {"perambalur", "veppanthattai", "kunnam", "alagapuram"}
    },
    "pudukkottai": {
        "district": "Pudukkottai",
        "state": "Tamil Nadu",
        "cities_towns": {"pudukkottai", "aranthangi", "viralimalai", "gandarvakottai", "thirumayam", "ponnamaravathi"}
    },
    "ramanathapuram": {
        "district": "Ramanathapuram",
        "state": "Tamil Nadu",
        "cities_towns": {"ramanathapuram", "ramnad", "rameswaram", "paramakudi", "kilakarai", "mudukulathur"}
    },
    "ranipet": {
        "district": "Ranipet",
        "state": "Tamil Nadu",
        "cities_towns": {"ranipet", "arrakonam", "arakkonam", "arcot", "walajah", "sholinghur"}
    },
    "salem": {
        "district": "Salem",
        "state": "Tamil Nadu",
        "cities_towns": {"salem", "mettur", "omalur", "attur", "sankari", "yercaud", "edappadi", "valapady"}
    },
    "sivaganga": {
        "district": "Sivaganga",
        "state": "Tamil Nadu",
        "cities_towns": {"sivaganga", "karaikudi", "devakottai", "manamadurai", "thirupuvanam", "kalaiyarkoil"}
    },
    "tenkasi": {
        "district": "Tenkasi",
        "state": "Tamil Nadu",
        "cities_towns": {"tenkasi", "sankarankovil", "kadayanallur", "courtallam", "puliangudi", "shenkottai"}
    },
    "thanjavur": {
        "district": "Thanjavur",
        "state": "Tamil Nadu",
        "cities_towns": {"thanjavur", "kumbakonam", "pattukkottai", "orathanadu", "thiruvaiyaru"}
    },
    "theni": {
        "district": "Theni",
        "state": "Tamil Nadu",
        "cities_towns": {"theni", "periyakulam", "bodinayakanur", "cumbum", "andipatti", "uthamapalayam"}
    },
    "thoothukudi": {
        "district": "Thoothukudi",
        "state": "Tamil Nadu",
        "cities_towns": {"thoothukudi", "tuticorin", "tiruchendur", "kovilpatti", "sathankulam", "srivaikuntam"}
    },
    "tiruchirappalli": {
        "district": "Tiruchirappalli",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruchirappalli", "trichy", "srirangam", "lalgudi", "manapparai", "thottiyam", "musiri"}
    },
    "tirunelveli": {
        "district": "Tirunelveli",
        "state": "Tamil Nadu",
        "cities_towns": {"tirunelveli", "palayamkottai", "nanguneri", "radhapuram", "ambasamudram"}
    },
    "tirupathur": {
        "district": "Tirupathur",
        "state": "Tamil Nadu",
        "cities_towns": {"tirupathur", "vaniyambadi", "ambur", "natarampalli"}
    },
    "tiruppur": {
        "district": "Tiruppur",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruppur", "tirupur", "avanashi", "udumalaipettai", "udumalpet", "dharapuram", "kangeyam", "palladam"}
    },
    "tiruvallur": {
        "district": "Tiruvallur",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruvallur", "avadi", "ponneri", "gummidipoondi", "tiruttani", "poonamallee"}
    },
    "tiruvannamalai": {
        "district": "Tiruvannamalai",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruvannamalai", "arani", "cheyyar", "polur", "chengam", "wandiwash"}
    },
    "tiruvarur": {
        "district": "Tiruvarur",
        "state": "Tamil Nadu",
        "cities_towns": {"tiruvarur", "mannargudi", "thiruthuraipoondi", "nannilam", "kodavasal"}
    },
    "vellore": {
        "district": "Vellore",
        "state": "Tamil Nadu",
        "cities_towns": {"vellore", "katpadi", "gudiyatham", "anaicut", "pernamallur"}
    },
    "viluppuram": {
        "district": "Viluppuram",
        "state": "Tamil Nadu",
        "cities_towns": {"viluppuram", "villupuram", "tindivanam", "gingee", "vanur"}
    },
    "virudhunagar": {
        "district": "Virudhunagar",
        "state": "Tamil Nadu",
        "cities_towns": {"virudhunagar", "sivakasi", "rajapalayam", "satur", "aruppukottai", "srivilliputhur"}
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
    Normalizes user-specified location string into structured target components with explicit location scope:
    target_country, target_state_or_ut, target_district, target_city, location_scope_type, valid_cities_in_district.
    Scope types: COUNTRY, STATE_UT, DISTRICT, CITY.
    """
    if not location_str:
        return {
            "target_country": "India",
            "target_state_or_ut": "Tamil Nadu",
            "target_district": "",
            "target_city": "",
            "location_scope_type": "STATE_UT",
            "valid_cities_in_district": set(),
            "raw_input": location_str
        }

    loc_low = location_str.lower().strip()

    # Explicit State/UT query for Puducherry UT
    is_explicit_ut = any(u in loc_low for u in ["puducherry ut", "pondicherry ut", "union territory", "puducherry state"])
    
    if is_explicit_ut:
        return {
            "target_country": "India",
            "target_state_or_ut": "Puducherry UT",
            "target_district": "",
            "target_city": "",
            "location_scope_type": "STATE_UT",
            "valid_cities_in_district": {"puducherry", "pondicherry", "pondy", "karaikal", "mahe", "yanam", "ouzhangarai", "moolakulam", "lawspet", "kalapet"},
            "raw_input": location_str
        }

    # Region specific sub-districts of Puducherry UT
    if "karaikal" in loc_low:
        return {
            "target_country": "India",
            "target_state_or_ut": "Puducherry UT",
            "target_district": "Karaikal",
            "target_city": "Karaikal",
            "location_scope_type": "DISTRICT",
            "valid_cities_in_district": {"karaikal", "kottucherry", "nedungadu", "neravy", "thirunallar", "t.r.pattinam"},
            "raw_input": location_str
        }
    elif "mahe" in loc_low:
        return {
            "target_country": "India",
            "target_state_or_ut": "Puducherry UT",
            "target_district": "Mahe",
            "target_city": "Mahe",
            "location_scope_type": "DISTRICT",
            "valid_cities_in_district": {"mahe", "chalakkara", "pandakkal"},
            "raw_input": location_str
        }
    elif "yanam" in loc_low:
        return {
            "target_country": "India",
            "target_state_or_ut": "Puducherry UT",
            "target_district": "Yanam",
            "target_city": "Yanam",
            "location_scope_type": "DISTRICT",
            "valid_cities_in_district": {"yanam"},
            "raw_input": location_str
        }
    elif any(p in loc_low for p in ["puducherry", "pondicherry", "pondy"]):
        return {
            "target_country": "India",
            "target_state_or_ut": "Puducherry UT",
            "target_district": "Puducherry",
            "target_city": "Puducherry",
            "location_scope_type": "DISTRICT",
            "valid_cities_in_district": {"puducherry", "pondicherry", "pondy", "ouzhangarai", "moolakulam", "lawspet", "kalapet"},
            "raw_input": location_str
        }

    # Match district in TN_DISTRICTS_DATA
    for dist_key, data in TN_DISTRICTS_DATA.items():
        if dist_key in loc_low or data["district"].lower() in loc_low or any(c in loc_low for c in data["cities_towns"]):
            canon_dist = normalize_district(data["district"])
            return {
                "target_country": "India",
                "target_state_or_ut": data["state"],
                "target_district": canon_dist,
                "target_city": canon_dist,
                "location_scope_type": "DISTRICT",
                "valid_cities_in_district": set(data["cities_towns"]),
                "raw_input": location_str
            }

    # Generic extraction for other locations
    tokens = [t for t in loc_low.split() if t not in ("in", "the", "and", "near", "district", "city", "ut", "state", "india")]
    raw_dist = tokens[0].capitalize() if tokens else loc_low.capitalize()
    canon_dist = normalize_district(raw_dist)
    
    return {
        "target_country": "India",
        "target_state_or_ut": "Tamil Nadu",
        "target_district": canon_dist,
        "target_city": canon_dist,
        "location_scope_type": "DISTRICT",
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
