from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import skills, health, auth, organizations
from app.core.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting up...")
    try:
        await auth.initialize_default_admin()
        logger.info("Default bootstrap admin initialized")
    except Exception as exc:
        logger.exception("Failed to initialize default bootstrap admin during startup: %s", exc)
        raise
    yield
    logger.info("Shutting down...")


bearer_scheme = HTTPBearer(auto_error=False)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Organization-Scoped Skill Registry for Jarvis AI COO",
    lifespan=lifespan,
    redirect_slashes=False,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(skills.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
    }


@app.get("/organizations")
async def get_organizations():
    """Get list of valid organizations"""
    return {"organizations": settings.organization_list}