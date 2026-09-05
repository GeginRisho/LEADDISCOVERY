from typing import Dict, Any, List

def clean_lead_data(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleans organization candidate fields and removes duplicate contacts.
    """
    # 1. Clean basic fields
    lead["name"] = lead["name"].strip()
    if lead.get("category"):
        lead["category"] = lead["category"].strip()
    if lead.get("address"):
        lead["address"] = lead["address"].strip()
    if lead.get("city"):
        lead["city"] = lead["city"].strip()
    if lead.get("state"):
        lead["state"] = lead["state"].strip()
    if lead.get("pincode"):
        lead["pincode"] = lead["pincode"].strip()

    # 2. Deduplicate emails
    seen_emails = set()
    unique_emails = []
    for email in lead.get("emails", []):
        email_val = email["email"].strip().lower()
        if email_val and email_val not in seen_emails:
            seen_emails.add(email_val)
            email["email"] = email_val
            unique_emails.append(email)
    lead["emails"] = unique_emails

    # 3. Deduplicate phones
    seen_phones = set()
    unique_phones = []
    for phone in lead.get("phones", []):
        norm_val = phone["normalized_value"].strip()
        if norm_val and norm_val not in seen_phones:
            seen_phones.add(norm_val)
            phone["normalized_value"] = norm_val
            phone["raw_value"] = phone["raw_value"].strip()
            unique_phones.append(phone)
    lead["phones"] = unique_phones

    # 4. Deduplicate social links
    seen_socials = set()
    unique_socials = []
    for social in lead.get("socials", []):
        url_val = social["url"].strip().lower()
        if url_val and url_val not in seen_socials:
            seen_socials.add(url_val)
            social["url"] = url_val
            unique_socials.append(social)
    lead["socials"] = unique_socials

    # 5. Deduplicate people
    seen_people = set()
    unique_people = []
    for person in lead.get("people", []):
        key = (person["name"].strip().lower(), person["designation"].strip().lower())
        if key[0] and key not in seen_people:
            seen_people.add(key)
            person["name"] = person["name"].strip()
            person["designation"] = person["designation"].strip()
            unique_people.append(person)
    lead["people"] = unique_people

    return lead
