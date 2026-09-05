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
    {"name": "Puducherry", "url": "https://py.gov.in/", "state": "Puducherry UT"},
    {"name": "Karaikal", "url": "https://karaikal.gov.in/", "state": "Puducherry UT"},
    {"name": "Mahe", "url": "https://mahe.gov.in/", "state": "Puducherry UT"},
    {"name": "Yanam", "url": "https://yanam.gov.in/", "state": "Puducherry UT"}
]


def seed_tn_districts(db: Session):
    for d in ALL_REGIONS:
        existing = db.query(District).filter(District.district_name == d["name"]).first()
        if not existing:
            dist = District(
                district_name=d["name"],
                state=d.get("state", "Tamil Nadu"),
                country="India",
                official_district_url=d["url"]
            )
            db.add(dist)
    db.commit()

