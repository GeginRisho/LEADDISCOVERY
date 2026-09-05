from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ScrapingTaskCreate(BaseModel):
    location: str = Field(..., description="Location, e.g., Puducherry")
    keyword: str = Field(..., description="Keyword or category, e.g., CBSE Schools")
    radius: Optional[int] = Field(None, description="Optional search radius in km")
    max_results: int = Field(100, ge=1, le=500, description="Maximum organizations to discover")
    max_pages_per_site: int = Field(20, ge=1, le=100, description="Maximum pages to crawl per website")
    requested_fields: List[str] = Field(
        default=["name", "phone", "email", "website", "address", "socials"],
        description="Fields to attempt extracting"
    )
    required_fields: List[str] = Field(
        default=[],
        description="Fields required for a lead to qualify in final results"
    )

class ScrapingTaskResponse(BaseModel):
    id: int
    public_task_id: str
    user_id: Optional[int] = None
    user_email: Optional[str] = "System/Guest"
    location: str
    keyword: str
    radius: Optional[int] = None
    max_results: int = 100
    max_pages_per_site: int = 20
    requested_fields: Optional[List[str]] = None
    required_fields: Optional[List[str]] = None
    status: str = "PENDING"
    progress: int = 0
    discovered_count: int = 0
    websites_found: int = 0
    websites_crawled: int = 0
    phone_count: int = 0
    email_count: int = 0
    address_count: int = 0
    social_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    lead_count: int = 0
    error_info: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ScrapingLogResponse(BaseModel):
    id: int
    task_id: int
    event_type: str
    message: str
    metadata_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
