import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

# Load local environment files before config import
load_dotenv()

from app.core.config import settings
from app.core.database import engine, Base, migrate_schema
from app.api import auth, tasks, leads, admin, organizations, campaigns, search

# Create database tables automatically on startup
try:
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    migrate_schema(engine)
    print("Database tables initialized successfully.")
    
    # Auto-seed Tamil Nadu districts & default users
    from app.core.database import SessionLocal
    from app.core.tn_districts import seed_tn_districts
    from app.api.auth import seed_default_users
    
    db_init = SessionLocal()
    try:
        seed_tn_districts(db_init)
        seed_default_users(db_init)
    finally:
        db_init.close()
except Exception as e:
    print(f"Error initializing database tables: {e}")

app = FastAPI(
    title="Web Scraping & Lead Discovery API",
    description="API for managing automated scraping tasks and leads extraction.",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(search.router, prefix="/api")

@app.get("/", include_in_schema=False)
def root():
    # Redirect root to OpenAPI docs
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
