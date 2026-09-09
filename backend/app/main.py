import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

print("[STARTUP] Process starting")
print("[STARTUP] Loading configuration")
load_dotenv()

import threading
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base, migrate_schema
from app.api import auth, tasks, leads, admin, organizations, campaigns, search

print("[STARTUP] Registering routes")

def init_db_background():
    """
    Non-blocking background worker for DB table creation, migrations, and seeding.
    Runs asynchronously in a separate thread so server port binding is never blocked.
    """
    print("[STARTUP] Database initialization started")
    try:
        Base.metadata.create_all(bind=engine)
        migrate_schema(engine)
        
        from app.core.database import SessionLocal
        from app.core.tn_districts import seed_tn_districts
        from app.api.auth import seed_default_users
        
        db_init = SessionLocal()
        try:
            seed_tn_districts(db_init)
            seed_default_users(db_init)
        finally:
            db_init.close()
        print("[STARTUP] Database initialization completed")
    except Exception as e:
        print(f"[STARTUP] Database initialization notice: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] FastAPI application ready")
    print("[STARTUP] Health endpoint available at /health")
    # Launch background DB sync without blocking HTTP server availability
    threading.Thread(target=init_db_background, daemon=True, name="db_init_worker").start()
    yield
    print("[SHUTDOWN] Application shutting down")

app = FastAPI(
    title="Web Scraping & Lead Discovery API",
    description="API for managing automated scraping tasks and leads extraction.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
def parse_cors_origins():
    origins_str = getattr(settings, "CORS_ORIGINS", "")
    if isinstance(origins_str, list):
        origins = origins_str
    elif isinstance(origins_str, str) and origins_str.strip():
        origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    else:
        origins = []
    
    defaults = [
        "https://leaddiscovery.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    for d in defaults:
        if d not in origins:
            origins.append(d)
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
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

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def root():
    # Redirect root to OpenAPI docs
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
