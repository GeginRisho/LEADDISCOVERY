import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, 
    JSON, Enum, Text, UniqueConstraint, Index, Boolean
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="USER", nullable=False) # USER, ADMIN
    status = Column(String(50), default="ACTIVE", nullable=False) # ACTIVE, SUSPENDED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tasks = relationship("ScrapingTask", back_populates="user")

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    district_name = Column(String(100), unique=True, index=True, nullable=False)
    state = Column(String(100), default="Tamil Nadu", nullable=False)
    country = Column(String(100), default="India", nullable=False)
    official_district_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ScrapingTask(Base):
    __tablename__ = "scraping_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    public_task_id = Column(String(50), unique=True, index=True, nullable=False)
    location = Column(String(255), nullable=False)
    keyword = Column(String(255), nullable=False)
    radius = Column(Integer, nullable=True)
    max_results = Column(Integer, default=100)
    max_pages_per_site = Column(Integer, default=20)
    requested_fields = Column(JSON, nullable=True) # Store list of strings to extract
    required_fields = Column(JSON, nullable=True) # Store list of qualification gate fields
    
    status = Column(String(50), default="PENDING") # PENDING, RUNNING, COMPLETED, COMPLETED_BELOW_MINIMUM, COMPLETED_WITH_NO_RESULTS, FAILED, CANCELLED
    progress = Column(Integer, default=0) # 0 to 100
    
    discovered_count = Column(Integer, default=0)
    websites_found = Column(Integer, default=0)
    websites_crawled = Column(Integer, default=0)
    phone_count = Column(Integer, default=0)
    email_count = Column(Integer, default=0)
    address_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    new_organizations_count = Column(Integer, default=0)
    updated_organizations_count = Column(Integer, default=0)
    
    error_info = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="tasks")
    organizations = relationship("Organization", back_populates="task")
    task_leads = relationship("TaskLead", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("ScrapingLog", back_populates="task", cascade="all, delete-orphan")

    @property
    def user_email(self) -> str:
        return self.user.email if self.user else "System/Guest"

    @property
    def lead_count(self) -> int:
        return len(self.task_leads) if self.task_leads else (len(self.organizations) if self.organizations else 0)

    @property
    def social_count(self) -> int:
        count = 0
        if self.task_leads:
            for tl in self.task_leads:
                if tl.organization:
                    count += len(tl.organization.social_links) if tl.organization.social_links else 0
        elif self.organizations:
            for org in self.organizations:
                count += len(org.social_links) if org.social_links else 0
        return count

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("scraping_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True, index=True)
    sub_category = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    discovery_source_url = Column(Text, nullable=True) # E.g. DuckDuckGo / SARAS directory URL
    
    # Address & Location details
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), default="India", nullable=False)
    pincode = Column(String(50), nullable=True)
    
    official_website_url = Column(Text, nullable=True)
    google_maps_url = Column(Text, nullable=True)
    
    # Official Social & Custom Links
    facebook_url = Column(Text, nullable=True)
    instagram_url = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    youtube_url = Column(Text, nullable=True)
    x_url = Column(Text, nullable=True)
    whatsapp_url = Column(Text, nullable=True)
    other_links = Column(JSON, nullable=True) # List of dicts: [{label, url, link_type}]
    
    # Verification Pipeline Flags
    admin_verified = Column(Boolean, default=False, index=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    identity_verified = Column(Boolean, default=False)
    category_verified = Column(Boolean, default=False)
    country_verified = Column(Boolean, default=False)
    state_verified = Column(Boolean, default=False)
    district_verified = Column(Boolean, default=False)
    city_verified = Column(Boolean, default=False)
    location_verified = Column(Boolean, default=False)
    official_website_verified = Column(Boolean, default=False)
    
    verification_source = Column(String(100), nullable=True)
    verification_reason = Column(Text, nullable=True)
    confidence_score = Column(String(50), default="LOW")
    
    confidence = Column(String(50), default="LOW") # HIGH, MEDIUM, LOW
    source_type = Column(String(50), default="SCRAPER_VERIFIED") # SCRAPER_VERIFIED, ADMIN_VERIFIED
    verification_method = Column(String(100), nullable=True) # ADMIN, SCRAPER_AUTOMATIC
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_crawled_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    task = relationship("ScrapingTask", back_populates="organizations")
    task_leads = relationship("TaskLead", back_populates="organization", cascade="all, delete-orphan")
    district_obj = relationship("District")
    website = relationship("Website", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    phone_numbers = relationship("PhoneNumber", back_populates="organization", cascade="all, delete-orphan")
    email_addresses = relationship("EmailAddress", back_populates="organization", cascade="all, delete-orphan")
    social_links = relationship("SocialLink", back_populates="organization", cascade="all, delete-orphan")
    branches = relationship("OrgBranch", back_populates="organization", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_org_name", "name"),
        Index("idx_org_district", "district"),
        Index("idx_org_category", "category"),
        Index("idx_org_sub_category", "sub_category"),
        Index("idx_org_admin_verified", "admin_verified"),
        Index("idx_org_cat_sub_dist", "category", "sub_category", "district"),
        Index("idx_org_cat_sub_city", "category", "sub_category", "city"),
        Index("idx_org_cat_sub_state", "category", "sub_category", "state"),
        Index("idx_org_loc_full", "country", "state", "district"),
        Index("idx_org_verified_all", "location_verified", "official_website_verified", "identity_verified", "category_verified"),
        Index("idx_org_fast_cat_dist", "category", "district", "admin_verified", "official_website_verified"),
        Index("idx_org_fast_cat_subcat_dist", "category", "sub_category", "district", "admin_verified", "official_website_verified"),
        Index("idx_org_fast_cat_state", "category", "state", "admin_verified", "official_website_verified"),
        Index("idx_org_fast_cat_city", "category", "city", "admin_verified", "official_website_verified"),
    )

class OrgBranch(Base):
    __tablename__ = "org_branches"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), default="India", nullable=False)
    pincode = Column(String(50), nullable=True)
    phone_numbers = Column(JSON, nullable=True)
    email_addresses = Column(JSON, nullable=True)
    website_url = Column(Text, nullable=True)
    maps_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="branches")

    __table_args__ = (
        Index("idx_branch_district", "district"),
        Index("idx_branch_city", "city"),
        Index("idx_branch_state", "state"),
    )

class DiscoveryCampaign(Base):
    __tablename__ = "discovery_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    region_scope = Column(String(100), default="TAMIL_NADU") # TAMIL_NADU, PUDUCHERRY, ALL
    category = Column(String(255), nullable=False) # Colleges, Hotels, Hospitals, Companies, IT Companies
    max_results_per_region = Column(Integer, default=15)
    max_pages_per_site = Column(Integer, default=5)
    
    status = Column(String(50), default="PENDING") # PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
    total_regions = Column(Integer, default=0)
    completed_regions = Column(Integer, default=0)
    failed_regions = Column(Integer, default=0)
    
    discovered_count = Column(Integer, default=0)
    new_orgs_count = Column(Integer, default=0)
    updated_orgs_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    items = relationship("CampaignItem", back_populates="campaign", cascade="all, delete-orphan")

class CampaignItem(Base):
    __tablename__ = "campaign_items"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("discovery_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    region_name = Column(String(100), nullable=False)
    category = Column(String(255), nullable=False)
    task_id = Column(Integer, ForeignKey("scraping_tasks.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(String(50), default="PENDING") # PENDING, RUNNING, COMPLETED, COMPLETED_WITH_NO_RESULTS, FAILED, TIMEOUT, BLOCKED, CANCELLED
    discovered_count = Column(Integer, default=0)
    new_orgs_count = Column(Integer, default=0)
    updated_orgs_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_info = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    campaign = relationship("DiscoveryCampaign", back_populates="items")
    task = relationship("ScrapingTask")

class TaskLead(Base):
    __tablename__ = "task_leads"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("scraping_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("org_branches.id", ondelete="SET NULL"), nullable=True, index=True)
    qualification_status = Column(String(50), default="QUALIFIED") # QUALIFIED, REJECTED
    confidence = Column(String(50), default="LOW")
    identity_verified = Column(Boolean, default=True)
    category_verified = Column(Boolean, default=True)
    location_verified = Column(Boolean, default=True)
    official_website_verified = Column(Boolean, default=True)
    verification_reason = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("ScrapingTask", back_populates="task_leads")
    organization = relationship("Organization", back_populates="task_leads")
    branch = relationship("OrgBranch")

    __table_args__ = (
        UniqueConstraint("task_id", "organization_id", name="uq_task_org_lead"),
        Index("idx_task_lead_task_id", "task_id"),
        Index("idx_task_lead_org_id", "organization_id"),
    )

class Website(Base):
    __tablename__ = "websites"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    domain = Column(String(255), nullable=True, index=True)
    url = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE") # ACTIVE, BLOCKED, FAILED, NO_OFFICIAL_WEBSITE
    reason = Column(String(255), nullable=True) # ROBOTS_DISALLOWED, TIMEOUT, CONNECTION_ERROR, etc.
    discovery_source = Column(String(100), nullable=True)
    confidence = Column(String(50), default="LOW")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    organization = relationship("Organization", back_populates="website")
    source_pages = relationship("SourcePage", back_populates="website", cascade="all, delete-orphan")

class SourcePage(Base):
    __tablename__ = "source_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    website = relationship("Website", back_populates="source_pages")
    phone_numbers = relationship("PhoneNumber", back_populates="source_page")
    email_addresses = relationship("EmailAddress", back_populates="source_page")
    social_links = relationship("SocialLink", back_populates="source_page")

class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_page_id = Column(Integer, ForeignKey("source_pages.id", ondelete="SET NULL"), nullable=True)
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(String(100), nullable=False, index=True)
    type = Column(String(50), default="main") # main, alternate, office, admissions, landline, whatsapp
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    organization = relationship("Organization", back_populates="phone_numbers")
    source_page = relationship("SourcePage", back_populates="phone_numbers")

class EmailAddress(Base):
    __tablename__ = "email_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_page_id = Column(Integer, ForeignKey("source_pages.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(255), nullable=False, index=True)
    extraction_method = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    organization = relationship("Organization", back_populates="email_addresses")
    source_page = relationship("SourcePage", back_populates="email_addresses")

class SocialLink(Base):
    __tablename__ = "social_links"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_page_id = Column(Integer, ForeignKey("source_pages.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(50), nullable=False) # facebook, instagram, linkedin, youtube, other
    url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    organization = relationship("Organization", back_populates="social_links")
    source_page = relationship("SourcePage", back_populates="social_links")

class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("scraping_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False) # TASK_CREATED, DISCOVERY_STARTED, etc.
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    task = relationship("ScrapingTask", back_populates="logs")
