from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import District

TAMIL_NADU_DISTRICTS = [
    {"name": "Ariyalur", "url": "https://ariyalur.nic.in/"},
    {"name": "Chengalpattu", "url": "https://chengalpattu.nic.in/"},
    {"name": "Chennai", "url": "https://chennai.nic.in/"},
    {"name": "Coimbatore", "url": "https://coimbatore.nic.in/"},
    {"name": "Cuddalore", "url": "https://cuddalore.nic.in/"},
    {"name": "Dharmapuri", "url": "https://dharmapuri.nic.in/"},
    {"name": "Dindigul", "url": "https://dindigul.nic.in/"},
    {"name": "Erode", "url": "https://erode.nic.in/"},
    {"name": "Kallakurichi", "url": "https://kallakurichi.nic.in/"},
    {"name": "Kancheepuram", "url": "https://kancheepuram.nic.in/"},
    {"name": "Kanniyakumari", "url": "https://kanniyakumari.nic.in/"},
    {"name": "Karur", "url": "https://karur.nic.in/"},
    {"name": "Krishnagiri", "url": "https://krishnagiri.nic.in/"},
    {"name": "Madurai", "url": "https://madurai.nic.in/"},
    {"name": "Mayiladuthurai", "url": "https://mayiladuthurai.nic.in/"},
    {"name": "Nagapattinam", "url": "https://nagapattinam.nic.in/"},
    {"name": "Namakkal", "url": "https://namakkal.nic.in/"},
    {"name": "Nilgiris", "url": "https://nilgiris.nic.in/"},
    {"name": "Perambalur", "url": "https://perambalur.nic.in/"},
    {"name": "Pudukkottai", "url": "https://pudukkottai.nic.in/"},
    {"name": "Ramanathapuram", "url": "https://ramanathapuram.nic.in/"},
    {"name": "Ranipet", "url": "https://ranipet.nic.in/"},
    {"name": "Salem", "url": "https://salem.nic.in/"},
    {"name": "Sivaganga", "url": "https://sivaganga.nic.in/"},
    {"name": "Tenkasi", "url": "https://tenkasi.nic.in/"},
    {"name": "Thanjavur", "url": "https://thanjavur.nic.in/"},
    {"name": "Theni", "url": "https://theni.nic.in/"},
    {"name": "Thoothukudi", "url": "https://thoothukudi.nic.in/"},
    {"name": "Tiruchirappalli", "url": "https://tiruchirappalli.nic.in/"},
    {"name": "Tirunelveli", "url": "https://tirunelveli.nic.in/"},
    {"name": "Tirupathur", "url": "https://tirupathur.nic.in/"},
    {"name": "Tiruppur", "url": "https://tiruppur.nic.in/"},
    {"name": "Tiruvallur", "url": "https://tiruvallur.nic.in/"},
    {"name": "Tiruvannamalai", "url": "https://tiruvannamalai.nic.in/"},
    {"name": "Tiruvarur", "url": "https://tiruvarur.nic.in/"},
    {"name": "Vellore", "url": "https://vellore.nic.in/"},
    {"name": "Viluppuram", "url": "https://viluppuram.nic.in/"},
    {"name": "Virudhunagar", "url": "https://virudhunagar.nic.in/"}
]

ALL_REGIONS = TAMIL_NADU_DISTRICTS + [
    {"name": "Puducherry", "url": "https://py.gov.in/", "state": "Puducherry UT"}
]

CANONICAL_DISTRICT_ALIASES = {
    "kanchipuram": "Kancheepuram",
    "kancheepuram": "Kancheepuram",
    "pondicherry": "Puducherry",
    "pondy": "Puducherry",
    "puducherry": "Puducherry",
    "puducherry ut": "Puducherry",
    "karaikal": "Puducherry",
    "mahe": "Puducherry",
    "yanam": "Puducherry",
    "tirupur": "Tiruppur",
    "tiruppur": "Tiruppur",
    "trichy": "Tiruchirappalli",
    "tiruchirapalli": "Tiruchirappalli",
    "tiruchirappalli": "Tiruchirappalli",
    "tuticorin": "Thoothukudi",
    "thoothukudi": "Thoothukudi",
    "villupuram": "Viluppuram",
    "viluppuram": "Viluppuram",
    "kanyakumari": "Kanniyakumari",
    "nagercoil": "Kanniyakumari",
    "kanniyakumari": "Kanniyakumari",
    "ramnad": "Ramanathapuram",
    "ramanathapuram": "Ramanathapuram",
    "thiruvarur": "Tiruvarur",
    "tiruvarur": "Tiruvarur",
    "udhagamandalam": "Nilgiris",
    "ooty": "Nilgiris",
    "nilgiris": "Nilgiris"
}

# Build canonical mapping from all 39 region names
CANONICAL_REGIONS_MAP = {r["name"].lower(): r["name"] for r in ALL_REGIONS}
for alias, target in CANONICAL_DISTRICT_ALIASES.items():
    CANONICAL_REGIONS_MAP[alias.lower()] = target

def normalize_district(district_name: Optional[str]) -> str:
    """
    Resolves alternate spellings and regional aliases to canonical district names.
    Guarantees 38 TN districts + 1 Puducherry UT row (39 total).
    """
    if not district_name:
        return ""
    clean = district_name.strip()
    clean_low = clean.lower()

    if clean_low in CANONICAL_REGIONS_MAP:
        return CANONICAL_REGIONS_MAP[clean_low]

    # Partial match check against canonical regions map
    for alias, canonical in CANONICAL_REGIONS_MAP.items():
        if len(alias) >= 4 and (alias in clean_low or clean_low in alias):
            return canonical

    return clean.title()

def seed_tn_districts(db: Session):
    for d in ALL_REGIONS:
        existing = db.query(District).filter(District.district_name == d["name"]).first()
        target_state = d.get("state", "Tamil Nadu")
        if not existing:
            dist = District(
                district_name=d["name"],
                state=target_state,
                country="India",
                official_district_url=d["url"]
            )
            db.add(dist)
        elif existing.state != target_state:
            existing.state = target_state
    db.commit()


