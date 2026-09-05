import re
import urllib.parse
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Set

# Regex patterns
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
OBFUSCATED_EMAIL_REGEX = re.compile(
    r'([a-zA-Z0-9._%+-]+)\s*[\(\[\{]\s*(?:at|\[at\]|at_dot)\s*[\)\]\}]\s*([a-zA-Z0-9.-]+)\s*[\(\[\{]?\s*(?:dot|\.)\s*[\)\]\}]?\s*([a-zA-Z]{2,})',
    re.IGNORECASE
)

# Phone regex (matches local formats, landlines, and E.164-ish formats)
PHONE_REGEX = re.compile(
    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}'
)

PINCODE_REGEX = re.compile(r'\b\d{3}\s?\d{3}\b') # Matches 6-digit postal codes (e.g., India)

DESIGNATION_KEYWORDS = [
    "principal", "director", "chairman", "administrator", "head of institution",
    "vice principal", "correspondent", "manager", "dean", "founder", "trustee"
]

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Collapse multiple whitespaces and strip
    return re.sub(r'\s+', ' ', text).strip()

def normalize_email(email: str) -> str:
    return email.strip().lower()

def normalize_phone(phone_str: str) -> str:
    if not phone_str:
        return ""
    cleaned = re.sub(r'[^\d+]', '', phone_str.strip())
    digits_only = re.sub(r'\D', '', cleaned)

    # Validate digit length
    if not (7 <= len(digits_only) <= 12):
        return ""

    # Exclude common non-phone numbers
    # 1. 4-digit years (19XX, 20XX)
    if len(digits_only) == 4 and digits_only.startswith(('19', '20')):
        return ""
    # 2. 6-digit Pincodes / CBSE Affiliations / IDs
    if len(digits_only) == 6:
        return ""
    # 3. Repeated single digit or sequence (e.g., 0000000000, 1234567890)
    if len(set(digits_only)) == 1:
        return ""

    # Preserve explicit international + prefix (e.g., +1, +44, +91)
    if cleaned.startswith("+"):
        if cleaned.startswith("+1"):
            # Return US/Canada number as +1... NEVER convert to +91
            return cleaned
        elif cleaned.startswith("+91"):
            return cleaned
        elif len(cleaned) >= 8:
            return cleaned

    # Indian Mobile (10 digits starting with 6-9)
    if len(digits_only) == 10 and digits_only[0] in "6789":
        return "+91" + digits_only

    # Indian Mobile or Landline with 91 prefix (12 digits)
    if len(digits_only) == 12 and digits_only.startswith("91"):
        return "+" + digits_only

    # Indian Landline with leading 0 (10 or 11 digits starting with 0)
    if digits_only.startswith("0") and len(digits_only) in (10, 11):
        return "+91" + digits_only[1:]

    # Standard Landline without 0, 7 to 11 digits
    if 7 <= len(digits_only) <= 11:
        return "+91" + digits_only

    return ""

def classify_phone(phone_raw: str, context_text: str) -> str:
    context = context_text.lower()
    if "admission" in context:
        return "admissions"
    elif "office" in context or "reception" in context:
        return "office"
    elif "whatsapp" in context or "wa.me" in context:
        return "whatsapp"
    elif phone_raw.startswith("+91") or (len(phone_raw) >= 10 and phone_raw.strip()[0] in "6789"):
        return "mobile"
    else:
        return "landline"

DUMMY_DOMAINS = {"domain.com", "yourdomain.com", "sample.com", "mytestsite.com", "placeholder.com"}
DUMMY_EMAILS = {"test@example.com", "user@example.com", "admin@example.com", "name@company.com", "email@example.com"}

def extract_emails(soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
    emails = []
    seen: Set[str] = set()
    INVALID_TLDS = {"learn", "at", "his", "he", "she", "from", "and", "the", "or", "to", "for", "with", "is", "by", "on", "png", "jpg", "jpeg", "svg", "webp"}

    def is_valid_real_email(em: str) -> bool:
        if em in DUMMY_EMAILS:
            return False
        parts = em.split("@")
        if len(parts) != 2:
            return False
        if parts[1] in DUMMY_DOMAINS:
            return False
        return True

    # 1. Extract from mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            email_part = href[7:].split("?")[0]
            email = normalize_email(email_part)
            if EMAIL_REGEX.match(email) and is_valid_real_email(email) and email not in seen:
                tld = email.split(".")[-1]
                if tld not in INVALID_TLDS:
                    seen.add(email)
                    emails.append({
                        "email": email,
                        "extraction_method": "mailto_link",
                        "source_url": url
                    })

    # 2. Extract from visible HTML text
    soup_clean = BeautifulSoup(str(soup), "lxml")
    for noise_tag in soup_clean(["script", "style", "noscript", "svg", "iframe", "path"]):
        noise_tag.decompose()

    text = soup_clean.get_text()
    for match in EMAIL_REGEX.findall(text):
        email = normalize_email(match)
        if is_valid_real_email(email) and email not in seen:
            tld = email.split(".")[-1]
            if tld.isalpha() and tld not in INVALID_TLDS:
                seen.add(email)
                emails.append({
                    "email": email,
                    "extraction_method": "regex_text",
                    "source_url": url
                })

    # 3. Extract obfuscated emails (e.g. info [at] school.com)
    for match in OBFUSCATED_EMAIL_REGEX.findall(text):
        email_str = f"{match[0]}@{match[1]}.{match[2]}"
        email = normalize_email(email_str)
        if EMAIL_REGEX.match(email) and is_valid_real_email(email) and email not in seen:
            tld = email.split(".")[-1]
            if tld.isalpha() and tld not in INVALID_TLDS:
                seen.add(email)
                emails.append({
                    "email": email,
                    "extraction_method": "obfuscated_regex_text",
                    "source_url": url
                })

    return emails

def extract_phones(soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
    phones = []
    seen: Set[str] = set()

    # 1. Extract from tel: links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("tel:"):
            raw_val = href[4:].split("?")[0]
            normalized = normalize_phone(raw_val)
            if normalized and normalized not in seen:
                seen.add(normalized)
                parent_text = a.get_text() + " " + (a.parent.get_text() if a.parent else "")
                phones.append({
                    "raw_value": raw_val,
                    "normalized_value": normalized,
                    "type": classify_phone(normalized, parent_text),
                    "source_url": url
                })

    # 2. Extract WhatsApp links (wa.me)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "wa.me" in href or "api.whatsapp.com/send" in href:
            parsed = urllib.parse.urlparse(href)
            phone_num = ""
            if "wa.me" in href:
                phone_num = parsed.path.replace("/", "")
            elif "phone" in urllib.parse.parse_qs(parsed.query):
                phone_num = urllib.parse.parse_qs(parsed.query)["phone"][0]
                
            phone_num = re.sub(r'\D', '', phone_num)
            if phone_num:
                normalized = normalize_phone(phone_num)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    phones.append({
                        "raw_value": href,
                        "normalized_value": normalized,
                        "type": "whatsapp",
                        "source_url": url
                    })

    # 3. Extract JSON-LD telephone fields
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, dict):
                tel = data.get("telephone")
                if tel:
                    tels = tel if isinstance(tel, list) else [tel]
                    for t in tels:
                        norm = normalize_phone(str(t))
                        if norm and norm not in seen:
                            seen.add(norm)
                            phones.append({
                                "raw_value": str(t),
                                "normalized_value": norm,
                                "type": classify_phone(norm, "schema.org JSON-LD"),
                                "source_url": url
                            })
        except Exception:
            pass

    # 4. Extract from visible text after decomposing script/style noise tags
    soup_clean = BeautifulSoup(str(soup), "lxml")
    for noise_tag in soup_clean(["script", "style", "noscript", "svg", "iframe", "path"]):
        noise_tag.decompose()

    text = soup_clean.get_text()
    
    # Phone context keywords
    contact_keywords = ["phone", "tel", "call", "mobile", "contact", "admission", "office", "fax", "reception", "principal"]

    for match in PHONE_REGEX.findall(text):
        normalized = normalize_phone(match)
        if normalized and normalized not in seen:
            # Check surrounding text context to ensure it's a real phone section
            idx = text.find(match)
            start = max(0, idx - 60)
            end = min(len(text), idx + len(match) + 60)
            context = text[start:end].lower()

            # Ensure contact context is present
            if any(kw in context for kw in contact_keywords) or normalized.startswith("+91"):
                seen.add(normalized)
                phones.append({
                    "raw_value": match.strip(),
                    "normalized_value": normalized,
                    "type": classify_phone(normalized, context),
                    "source_url": url
                })

    return phones

def extract_social_links(soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
    socials = []
    seen: Set[str] = set()
    
    platforms = {
        "facebook.com": "facebook",
        "instagram.com": "instagram",
        "linkedin.com": "linkedin",
        "youtube.com": "youtube",
        "twitter.com": "twitter",
        "x.com": "twitter"
    }
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        parsed = urllib.parse.urlparse(href)
        domain = parsed.netloc.lower()
        
        # Check platforms
        platform_matched = None
        for p_domain, p_name in platforms.items():
            if p_domain in domain or domain.endswith("." + p_domain):
                platform_matched = p_name
                break
                
        if platform_matched:
            # Normalize social URL (remove query parameters/hashes)
            normalized = f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path}"
            # Ignore root platform page, e.g. facebook.com/ or facebook.com/sharer
            path = parsed.path.lower()
            if len(path) <= 1 or "share" in path or "intent" in path or "widgets" in path:
                continue
                
            if normalized not in seen:
                seen.add(normalized)
                socials.append({
                    "platform": platform_matched,
                    "url": normalized,
                    "source_url": url
                })
                
    return socials

def extract_json_ld_address(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    # Look for JSON-LD schemas in script tags
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            # JSON-LD can be a single object or list
            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                continue
                
            for item in items:
                # Check for Organization/LocalBusiness type
                if item.get("@type") in ("Organization", "LocalBusiness", "School", "EducationalOrganization"):
                    addr = item.get("address")
                    if isinstance(addr, dict):
                        return {
                            "address": addr.get("streetAddress") or addr.get("name") or "",
                            "city": addr.get("addressLocality") or "",
                            "state": addr.get("addressRegion") or "",
                            "pincode": addr.get("postalCode") or ""
                        }
                    elif isinstance(addr, str):
                        # Attempt to parse postal code from string address
                        pincode_match = PINCODE_REGEX.search(addr)
                        return {
                            "address": addr,
                            "city": "",
                            "state": "",
                            "pincode": pincode_match.group(0) if pincode_match else ""
                        }
        except Exception:
            continue
    return None

def extract_address_from_html(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    # 1. Check Schema.org microdata (itemprop="address")
    addr_elem = soup.find(itemprop="address")
    if addr_elem:
        street = addr_elem.find(itemprop="streetAddress")
        locality = addr_elem.find(itemprop="addressLocality")
        region = addr_elem.find(itemprop="addressRegion")
        postcode = addr_elem.find(itemprop="postalCode")
        
        street_val = street.get_text(strip=True) if street else ""
        city_val = locality.get_text(strip=True) if locality else ""
        state_val = region.get_text(strip=True) if region else ""
        pin_val = postcode.get_text(strip=True) if postcode else ""
        
        full_addr = street_val or addr_elem.get_text(strip=True)
        return {
            "address": full_addr,
            "city": city_val,
            "state": state_val,
            "pincode": pin_val
        }

    # 2. Check footer or contact divs for pincode match
    # Usually address has a pincode near it
    for element in soup.find_all(["footer", "div", "p", "address"]):
        # Limit text size to check specific segments
        elem_text = element.get_text(" ", strip=True)
        if len(elem_text) < 300:
            match = PINCODE_REGEX.search(elem_text)
            if match and ("address" in elem_text.lower() or "reach" in elem_text.lower() or "contact" in elem_text.lower() or "road" in elem_text.lower() or "street" in elem_text.lower()):
                pincode = match.group(0)
                # Split and take surrounding words as address
                return {
                    "address": clean_text(elem_text),
                    "city": "",
                    "state": "",
                    "pincode": pincode
                }
                
    return None

def extract_contact_person(soup: BeautifulSoup, url: str) -> List[Dict[str, Any]]:
    people = []
    seen_names = set()
    
    # Heuristics: search for designations followed/preceded by names
    # e.g., "Principal: Dr. R. Murugan" or "Dr. John Doe, Chairman"
    text = soup.get_text()
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    for line in lines:
        if len(line) > 100:
            continue
        line_lower = line.lower()
        
        for designation in DESIGNATION_KEYWORDS:
            if designation in line_lower:
                # Find name candidates in same line
                # Look for titles like Dr., Mr., Mrs., Prof., or capitalized words
                name_match = re.search(
                    r'(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.)\s*[A-Z][a-zA-Z\s\.]+',
                    line
                )
                if name_match:
                    name = clean_text(name_match.group(0))
                    if name not in seen_names:
                        seen_names.add(name)
                        people.append({
                            "name": name,
                            "designation": designation.title(),
                            "source_url": url
                        })
                else:
                    # Look for capitalized words near the designation
                    # e.g. "John Doe, Principal"
                    parts = re.split(r'[,:\-]', line)
                    for part in parts:
                        part = part.strip()
                        # If part is 2-3 capitalized words, treat as name
                        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$', part):
                            if part.lower() not in DESIGNATION_KEYWORDS:
                                if part not in seen_names:
                                    seen_names.add(part)
                                    people.append({
                                        "name": part,
                                        "designation": designation.title(),
                                        "source_url": url
                                    })
                                    
    return people
