from bs4 import BeautifulSoup
from app.services.scraper.extractor import (
    extract_emails, extract_phones, extract_social_links,
    extract_json_ld_address, extract_address_from_html, extract_contact_person
)

def test_email_extraction():
    html = """
    <html>
        <body>
            <p>Contact us at info@example.com or support@example-school.edu</p>
            <a href="mailto:admin@example.org?subject=Query">Email Admin</a>
            <p>Our principal's email is principal [at] example.com</p>
            <p>Fake emails: fake@, @example.com, info@example.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    url = "https://example.com/contact"
    emails = extract_emails(soup, url)
    
    # We expect info@example.com, support@example-school.edu, admin@example.org, principal@example.com
    extracted_values = {e["email"] for e in emails}
    assert "info@example.com" in extracted_values
    assert "support@example-school.edu" in extracted_values
    assert "admin@example.org" in extracted_values
    assert "principal@example.com" in extracted_values
    assert len(emails) == 4

def test_phone_extraction():
    html = """
    <html>
        <body>
            <p>Call admissions at +91 98765 43210 or office: (0413) 223-4567</p>
            <a href="tel:+914131234567">Call Landline</a>
            <a href="https://wa.me/919999988888?text=Hello">WhatsApp us</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    url = "https://example.com/contact"
    phones = extract_phones(soup, url)
    
    normalized_values = {p["normalized_value"] for p in phones}
    assert "+919876543210" in normalized_values
    assert "+914131234567" in normalized_values
    assert "+919999988888" in normalized_values
    
    # Check types
    types = {p["type"] for p in phones}
    assert "admissions" in types or "mobile" in types
    assert "whatsapp" in types

def test_social_links_extraction():
    html = """
    <html>
        <body>
            <a href="https://www.facebook.com/exampleprofile">Facebook</a>
            <a href="https://instagram.com/exampleschool/?hl=en">Instagram</a>
            <a href="https://linkedin.com/school/example-school">LinkedIn</a>
            <a href="https://youtube.com/c/exampleschool">YouTube</a>
            <a href="https://facebook.com/sharer/sharer.php?u=example.com">Share Button</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    url = "https://example.com"
    socials = extract_social_links(soup, url)
    
    platforms = {s["platform"]: s["url"] for s in socials}
    assert "facebook" in platforms
    assert "instagram" in platforms
    assert "linkedin" in platforms
    assert "youtube" in platforms
    
    # Check normalization (query params stripped)
    assert platforms["instagram"] == "https://instagram.com/exampleschool/"
    # Share link should be ignored
    assert "sharer" not in "".join(platforms.values())

def test_address_extraction_json_ld():
    html = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "School",
                "name": "Example School",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "12 Main Street",
                    "addressLocality": "Puducherry",
                    "addressRegion": "Puducherry",
                    "postalCode": "605001"
                }
            }
            </script>
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    addr = extract_json_ld_address(soup)
    
    assert addr is not None
    assert addr["address"] == "12 Main Street"
    assert addr["city"] == "Puducherry"
    assert addr["pincode"] == "605001"

def test_address_extraction_html():
    html = """
    <html>
        <body>
            <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
                <span itemprop="streetAddress">45 Beach Road</span>
                <span itemprop="addressLocality">Puducherry</span>
                <span itemprop="postalCode">605003</span>
            </div>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    addr = extract_address_from_html(soup)
    
    assert addr is not None
    assert "45 Beach Road" in addr["address"]
    assert addr["city"] == "Puducherry"
    assert addr["pincode"] == "605003"

def test_contact_person_extraction():
    html = """
    <html>
        <body>
            <p>Principal: Dr. Murugan Swamy</p>
            <p>Our Chairman Mr. A. B. C. Ramanathan welcomes you.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    url = "https://example.com/about"
    people = extract_contact_person(soup, url)
    
    names = {p["name"] for p in people}
    designations = {p["designation"] for p in people}
    
    assert "Dr. Murugan Swamy" in names
    assert "Mr. A. B. C. Ramanathan" in names or "A. B. C. Ramanathan" in names or "Chairman" in designations
    assert "Principal" in designations
