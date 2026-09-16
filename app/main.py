"""
Land Stack India - API Gateway & Backend Application Entrypoint.
Orchestrates REST APIs, API Versioning, RBAC, Rate Limiting, CORS, and Data Platform.
Also hosts the merged interactive BhooNetra SIH Frontend.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from app.core.cache import cache
from app.core.dependencies import get_client_ip
from app.api.v1 import api_v1_router
from app.api.legacy_bridge import legacy_router
from app.seed_data import seed_database
from app.models.public_purchase import PublicPurchaseRequest  # noqa: F401 - registers table metadata
from app.models.notifications import NotificationRecord  # noqa: F401 - registers table metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle manager."""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Initialize operational sample data (synthetic records representing real-world cases)
    seed_database()
    yield
    print(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title="LAND STACK INDIA - National Digital Public Infrastructure",
    description="""
# LAND STACK INDIA BACKEND ARCHITECTURE
National Digital Public Infrastructure for Land Records & GIS Interoperability.

### Key Capabilities:
- **API Gateway**: REST APIs, API Versioning (`/api/v1`), Rate Limiting, Request Validation, CORS.
- **Three Core Portals**:
  - **Public Portal**: Open discovery, spatial cadastral map polygons, privacy-preserving DPDP-compliant ownership masking.
  - **Citizen Portal**: Authenticated OTP/JWT dashboard, title view, legal document extracts, and mutation application submission.
  - **Government Portal (RBAC)**: Role-Based Access Control (Super Admin, Revenue Officer, SRO, Planning Officer, Municipal Officer, Police Officer, Auditor).
- **Land Core Engine**: Configurable ULPIN (Bhu-Aadhaar), Parcel 360° Aggregation, Record of Rights (RoR), and SRO Registration.
- **GIS Engine**: PostGIS GeoJSON endpoints, multi-category spatial layers (Base, Governance, Planning, Utility, Environment), and spatial distance queries.
- **Workflow Engine**: 11-step Ownership Transfer & Mutation state machine with automated pipeline checks and officer reviews.
- **Document Service**: Cryptographic SHA-256 tamper-evident integrity verification.
- **Integration Layer**: State adapters for heterogeneous state systems (Tamil Nadu Nilam, Maharashtra MahaBhulekh, Karnataka Bhoomi) mapping into Canonical Land Model.
- **AI / ML Engine**: Temporal satellite optical change detection, multi-factor title fraud risk scoring, and predictive algorithmic valuation.
- **Audit Service**: Immutable, append-only security logs for all sensitive land actions.
- **Interactive Web Portal**: Built-in merged Leaflet GIS frontend with live analytics dashboard.
    """,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# -------------------------------------------------------------
# GATEWAY MIDDLEWARE: CORS
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# GATEWAY MIDDLEWARE: Rate Limiting & Gateway Logging
# -------------------------------------------------------------
@app.middleware("http")
async def rate_limiting_and_headers_middleware(request: Request, call_next):
    client_ip = get_client_ip(request)
    
    # Check rate limit (120 req/min per IP)
    allowed = cache.check_rate_limit(
        client_id=client_ip,
        max_requests=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60
    )
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Maximum 120 requests per minute allowed."}
        )

    response = await call_next(request)
    # Append custom Land Stack Gateway headers
    response.headers["X-Land-Stack-Gateway"] = "LandStack-India/1.0"
    response.headers["X-API-Version"] = settings.VERSION
    return response


# -------------------------------------------------------------
# MOUNT API ROUTERS
# -------------------------------------------------------------
# 1. Mount national versioned API (/api/v1/...)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# 2. Mount frontend compatibility bridge (/api/...)
app.include_router(legacy_router)

# 3. Mount Frontend UI
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")


@app.get("/", response_class=HTMLResponse, summary="Interactive Web Frontend")
def serve_frontend():
    """Serves the merged interactive BhooNetra GIS web application."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Land Stack India Backend Operational</h1><p>Visit <a href='/docs'>/docs</a> for Swagger API.</p>")


@app.get("/api-info", summary="Root Gateway Info")
def api_info():
    """JSON overview of national API gateway routing."""
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "OPERATIONAL",
        "documentation": "/docs",
        "portals": {
            "public": f"{settings.API_V1_STR}/public",
            "citizen": f"{settings.API_V1_STR}/citizen",
            "government": f"{settings.API_V1_STR}/government",
            "gis": f"{settings.API_V1_STR}/gis",
            "integration": f"{settings.API_V1_STR}/integration",
            "ai": f"{settings.API_V1_STR}/ai"
        },
        "frontend_ui": "/"
    }


@app.get("/health", summary="Health Check")
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "cache": "active",
        "gateway": "active"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
