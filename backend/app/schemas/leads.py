from pydantic import BaseModel, model_validator
from typing import List, Optional
from datetime import datetime

class PhoneNumberSchema(BaseModel):
    id: int
    raw_value: str
    normalized_value: str
    type: str
    source_page_url: Optional[str] = None
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def resolve_source_page_url(cls, data):
        # Resolve source_page.url relationship
        if hasattr(data, 'source_page') and data.source_page:
            data.source_page_url = data.source_page.url
        elif isinstance(data, dict):
            source_page = data.get('source_page')
            if source_page:
                data['source_page_url'] = getattr(source_page, 'url', None) or source_page.get('url')
        return data

    class Config:
        from_attributes = True

class EmailAddressSchema(BaseModel):
    id: int
    email: str
    extraction_method: Optional[str]
    source_page_url: Optional[str] = None
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def resolve_source_page_url(cls, data):
        if hasattr(data, 'source_page') and data.source_page:
            data.source_page_url = data.source_page.url
        elif isinstance(data, dict):
            source_page = data.get('source_page')
            if source_page:
                data['source_page_url'] = getattr(source_page, 'url', None) or source_page.get('url')
        return data

    class Config:
        from_attributes = True

class SocialLinkSchema(BaseModel):
    id: int
    platform: str
    url: str
    source_page_url: Optional[str] = None
    created_at: datetime

    @model_validator(mode='before')
    @classmethod
    def resolve_source_page_url(cls, data):
        if hasattr(data, 'source_page') and data.source_page:
            data.source_page_url = data.source_page.url
        elif isinstance(data, dict):
            source_page = data.get('source_page')
            if source_page:
                data['source_page_url'] = getattr(source_page, 'url', None) or source_page.get('url')
        return data

    class Config:
        from_attributes = True

class WebsiteSchema(BaseModel):
    id: int
    domain: Optional[str] = None
    url: Optional[str] = None
    status: str
    reason: Optional[str] = None
    confidence: str
    created_at: datetime

    class Config:
        from_attributes = True

class OrganizationLeadResponse(BaseModel):
    id: int
    task_id: Optional[int] = None
    name: str
    category: Optional[str] = None
    discovery_source_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    confidence: str
    created_at: datetime
    updated_at: datetime
    
    website: Optional[WebsiteSchema] = None
    phone_numbers: List[PhoneNumberSchema] = []
    email_addresses: List[EmailAddressSchema] = []
    social_links: List[SocialLinkSchema] = []

    class Config:
        from_attributes = True
