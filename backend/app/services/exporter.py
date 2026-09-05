import csv
import io
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

def csv_safe_val(val: Any) -> str:
    s = str(val or "").strip()
    # Prevent CSV formula injection (OWASP guideline: escape cells starting with =, +, -, @)
    if s.startswith(("=", "@")):
        return "'" + s
    elif s.startswith(("+", "-")) and not s[1:].isdigit():
        return "'" + s
    return s

def prepare_leads_df(leads: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for lead in leads:
        # Flatten phone numbers: "+919876543210 (admissions), +9111223344 (office)"
        phones_list = []
        for p in lead.get("phone_numbers", []):
            raw = p.get("raw_value", "")
            norm = p.get("normalized_value", "")
            ptype = p.get("type", "main")
            phones_list.append(f"{norm or raw} ({ptype})")
        phones_str = ", ".join(phones_list)
        
        # Flatten email addresses
        emails_list = [e.get("email", "") for e in lead.get("email_addresses", [])]
        emails_str = ", ".join(emails_list)
        
        # Flatten social links: "Facebook: http://..., Instagram: http://..."
        socials_list = [f"{s.get('platform', 'other')}: {s.get('url', '')}" for s in lead.get("social_links", [])]
        socials_str = ", ".join(socials_list)
        
        # Contact person: "Principal: Dr. John"
        people_list = [f"{p.get('name', '')} ({p.get('designation', 'contact')})" for p in lead.get("people", [])]
        if not people_list and lead.get("contact_person"):
            people_list = [f"{lead.get('contact_person')} ({lead.get('designation', 'contact')})"]
        people_str = ", ".join(people_list)
        
        # Official website
        website_url = ""
        website_obj = lead.get("website")
        if website_obj:
            website_url = website_obj.get("url") or ""
        elif lead.get("possible_website"):
            website_url = lead.get("possible_website")
            
        # Source page
        source_url = lead.get("source_url") or ""
        if not source_url and lead.get("phone_numbers"):
            source_url = lead.get("phone_numbers")[0].get("source_page_url") or ""
        if not source_url and lead.get("email_addresses"):
            source_url = lead.get("email_addresses")[0].get("source_page_url") or ""

        rows.append({
            "Organization Name": csv_safe_val(lead.get("name")),
            "Category": csv_safe_val(lead.get("category")),
            "Official Website": csv_safe_val(website_url),
            "Phone Numbers": csv_safe_val(phones_str),
            "Emails": csv_safe_val(emails_str),
            "Address": csv_safe_val(lead.get("address")),
            "City": csv_safe_val(lead.get("city")),
            "State": csv_safe_val(lead.get("state")),
            "Pincode": csv_safe_val(lead.get("pincode")),
            "Social Links": csv_safe_val(socials_str),
            "Contact Person(s)": csv_safe_val(people_str),
            "Confidence Level": csv_safe_val(lead.get("confidence", "LOW")),
            "Primary Source URL": csv_safe_val(source_url),
            "Scraped Date": lead.get("created_at").strftime("%Y-%m-%d %H:%M:%S") if isinstance(lead.get("created_at"), datetime) else str(lead.get("created_at") or "")
        })
        
    return pd.DataFrame(rows)

def export_leads_to_csv(leads: List[Dict[str, Any]]) -> str:
    df = prepare_leads_df(leads)
    
    # We output to a string buffer using standard python csv mechanisms for 100% control
    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens it with correct formatting
    output.write('\ufeff')
    df.to_csv(output, index=False, quoting=csv.QUOTE_MINIMAL)
    return output.getvalue()

def export_leads_to_excel(leads: List[Dict[str, Any]]) -> bytes:
    df = prepare_leads_df(leads)
    
    output = io.BytesIO()
    # Write using openpyxl engine
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Leads")
    return output.getvalue()
