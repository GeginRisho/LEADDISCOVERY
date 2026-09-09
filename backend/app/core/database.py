import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import make_url
from app.core.config import settings

def create_database_if_not_exists():
    db_url = settings.DATABASE_URL
    if "sqlite" in db_url.lower():
        return
    try:
        url = make_url(db_url)
        db_name = url.database
        
        # Connect to the default 'postgres' database with a short timeout
        conn = psycopg2.connect(
            host=url.host or "localhost",
            port=url.port or 5432,
            user=url.username or "postgres",
            password=url.password or "",
            database="postgres",
            connect_timeout=3
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f"CREATE DATABASE {db_name}")
        
        cursor.close()
        conn.close()
    except Exception:
        pass

# Safe database environment detection without logging credentials
db_url_parsed = make_url(settings.DATABASE_URL)
db_host = db_url_parsed.host or "localhost"
db_name = db_url_parsed.database or "leaddiscovery"
db_type = "SQLite Local" if "sqlite" in settings.DATABASE_URL.lower() else ("Neon PostgreSQL" if "neon.tech" in settings.DATABASE_URL.lower() else "PostgreSQL")
print(f"[STARTUP] Creating database engine ({db_type})")

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def migrate_schema(eng):
    statements = [
        "ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'USER'",
        "ALTER TABLE users ADD COLUMN status VARCHAR(50) DEFAULT 'ACTIVE'",
        "ALTER TABLE scraping_tasks ADD COLUMN user_id INTEGER NULL",
        "ALTER TABLE scraping_tasks ADD COLUMN requested_fields JSON NULL",
        "ALTER TABLE scraping_tasks ADD COLUMN required_fields JSON NULL",
        "ALTER TABLE scraping_tasks ALTER COLUMN required_fields DROP NOT NULL",
        "ALTER TABLE scraping_tasks ALTER COLUMN requested_fields DROP NOT NULL",
        "ALTER TABLE scraping_tasks ADD COLUMN new_organizations_count INTEGER DEFAULT 0",
        "ALTER TABLE scraping_tasks ADD COLUMN updated_organizations_count INTEGER DEFAULT 0",
        "ALTER TABLE organizations ALTER COLUMN task_id DROP NOT NULL",
        "ALTER TABLE organizations ADD COLUMN discovery_source_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN district_id INTEGER NULL",
        "ALTER TABLE organizations ADD COLUMN district VARCHAR(100) NULL",
        "ALTER TABLE organizations ADD COLUMN country VARCHAR(100) DEFAULT 'India'",
        "ALTER TABLE organizations ADD COLUMN official_website_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN identity_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN category_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN country_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN state_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN district_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN city_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN location_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN official_website_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN verification_source VARCHAR(100) NULL",
        "ALTER TABLE organizations ADD COLUMN verification_reason TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN confidence_score VARCHAR(50) DEFAULT 'LOW'",
        "ALTER TABLE organizations ADD COLUMN source_type VARCHAR(50) DEFAULT 'AUTOMATIC'",
        "ALTER TABLE organizations ADD COLUMN last_seen_at TIMESTAMP NULL",
        "ALTER TABLE organizations ADD COLUMN last_crawled_at TIMESTAMP NULL",
        "ALTER TABLE organizations ADD COLUMN last_verified_at TIMESTAMP NULL",
        "ALTER TABLE task_leads ADD COLUMN identity_verified BOOLEAN DEFAULT TRUE",
        "ALTER TABLE task_leads ADD COLUMN category_verified BOOLEAN DEFAULT TRUE",
        "ALTER TABLE task_leads ADD COLUMN location_verified BOOLEAN DEFAULT TRUE",
        "ALTER TABLE task_leads ADD COLUMN official_website_verified BOOLEAN DEFAULT TRUE",
        "ALTER TABLE task_leads ADD COLUMN verification_reason TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN display_name VARCHAR(255) NULL",
        "ALTER TABLE organizations ADD COLUMN description TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN google_maps_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN facebook_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN instagram_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN linkedin_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN youtube_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN x_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN whatsapp_url TEXT NULL",
        "ALTER TABLE organizations ADD COLUMN other_links JSON NULL",
        "ALTER TABLE organizations ADD COLUMN admin_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN verified_by VARCHAR(255) NULL",
        "ALTER TABLE organizations ADD COLUMN verified_at TIMESTAMP NULL",
        "ALTER TABLE organizations ADD COLUMN verification_method VARCHAR(100) NULL",
        "ALTER TABLE organizations ADD COLUMN previous_source_type VARCHAR(50) NULL",
        "ALTER TABLE organizations ADD COLUMN is_quarantined BOOLEAN DEFAULT FALSE",
        "ALTER TABLE organizations ADD COLUMN quarantine_reason TEXT NULL",
        "ALTER TABLE task_leads ADD COLUMN branch_id INTEGER NULL",
        "CREATE INDEX IF NOT EXISTS idx_org_admin_verified ON organizations(admin_verified)",
        "CREATE TABLE IF NOT EXISTS org_branches (id SERIAL PRIMARY KEY, organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, branch_name VARCHAR(255) NOT NULL, address TEXT, city VARCHAR(100), district VARCHAR(100), state VARCHAR(100), country VARCHAR(100) DEFAULT 'India', pincode VARCHAR(50), phone_numbers JSON, email_addresses JSON, website_url TEXT, maps_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE INDEX IF NOT EXISTS idx_branch_org ON org_branches(organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_branch_district ON org_branches(district)",
        "CREATE INDEX IF NOT EXISTS idx_branch_city ON org_branches(city)",
        "CREATE INDEX IF NOT EXISTS idx_branch_state ON org_branches(state)",
        "CREATE INDEX IF NOT EXISTS idx_org_category_district ON organizations(category, district)",
        "CREATE INDEX IF NOT EXISTS idx_org_district_city ON organizations(district, city)",
        "CREATE INDEX IF NOT EXISTS idx_org_verification ON organizations(admin_verified, confidence)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON scraping_tasks(user_id, status)",
        "ALTER TABLE scraping_tasks ADD COLUMN client_request_id VARCHAR(100) NULL",
        "CREATE INDEX IF NOT EXISTS idx_tasks_client_req ON scraping_tasks(client_request_id)",
    ]
    with eng.connect() as conn:
        for stmt in statements:
            try:
                with conn.begin():
                    conn.execute(text(stmt))
            except Exception:
                pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
