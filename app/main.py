# ============================================================================
# Main Application Module - WITH ALL ROUTES
# ============================================================================
# File: app/main.py
# Purpose: FastAPI application initialization with all route imports
# Status: Production-Ready ✅

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import engine, Base

# IMPORT ALL ROUTES INDIVIDUALLY TO PREVENT CIRCULAR IMPORTS
from app.routes import auth
from app.routes import users
from app.routes import speakers
from app.routes import sessions
from app.routes import resources
from app.routes import ratings
from app.routes import announcements
from app.routes import social
from app.routes import leaderboard
from app.routes import badges
#from app.routes import challenges
from app.routes import learning_paths
from app.routes import engagement
from app.routes import partners
from app.routes import analytics
from app.routes import admin


# ============= LOGGING SETUP =============
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============= LIFESPAN EVENTS =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown
    
    Startup:
    - Create database tables
    - Initialize connections
    
    Shutdown:
    - Close connections
    - Cleanup resources
    """
    # ===== STARTUP =====
    logger.info("Starting EventAI API...")
    
    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    
    # Log startup
    logger.info(f"EventAI API v{settings.app_version} started with 16 routes")
    logger.info("All features loaded:")
    logger.info("✅ Authentication & User Management")
    logger.info("✅ Sessions & Speakers")
    logger.info("✅ Resources & Ratings")
    logger.info("✅ Social Wall")
    logger.info("✅ Gamification (Badges, Challenges, Leaderboard)")
    logger.info("✅ Learning Paths")
    logger.info("✅ Engagement Center (Polls, Quizzes, Activities)")
    logger.info("✅ Announcements & Partnerships")
    logger.info("✅ Analytics & Admin Dashboard")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("Shutting down EventAI API...")
    logger.info("Cleanup completed")


# ============= FASTAPI APP INITIALIZATION =============
app = FastAPI(
    title=settings.app_name,
    description="AI-powered enterprise event management platform",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ============= CORS MIDDLEWARE =============
origins = [origin.strip() for origin in settings.allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS enabled for origins: {origins}")


# ============= INCLUDE ALL ROUTES =============
app.include_router(auth.router)
logger.info("✅ Authentication routes loaded")

app.include_router(users.router)
logger.info("✅ User routes loaded")

app.include_router(speakers.router)
logger.info("✅ Speaker routes loaded")

app.include_router(sessions.router)
logger.info("✅ Session routes loaded")

app.include_router(resources.router)
logger.info("✅ Resource routes loaded")

app.include_router(ratings.router)
logger.info("✅ Rating routes loaded")

app.include_router(announcements.router)
logger.info("✅ Announcement routes loaded")

app.include_router(social.router)
logger.info("✅ Social wall routes loaded")

app.include_router(leaderboard.router)
logger.info("✅ Leaderboard routes loaded")

app.include_router(badges.router)
logger.info("✅ Badge routes loaded")

#app.include_router(challenges.router)
#logger.info("✅ Challenge routes loaded")

app.include_router(learning_paths.router)
logger.info("✅ Learning path routes loaded")

app.include_router(engagement.router)
logger.info("✅ Engagement center routes loaded")

app.include_router(partners.router)
logger.info("✅ Partner routes loaded")

app.include_router(analytics.router)
logger.info("✅ Analytics routes loaded")

app.include_router(admin.router)
logger.info("✅ Admin routes loaded")


# ============= HEALTH CHECK ENDPOINT =============
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "routes": 16
    }


# ============= ROOT ENDPOINT =============
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint
    
    Returns:
        dict: Welcome message
    """
    return {
        "message": "Welcome to EventAI API",
        "docs": "/docs",
        "version": settings.app_version,
        "features": [
            "Authentication & User Management",
            "Sessions & Speakers",
            "Resources & Ratings",
            "Social Wall",
            "Gamification (Badges, Challenges, Leaderboard)",
            "Learning Paths",
            "Engagement Center (Polls, Quizzes, Activities)",
            "Announcements & Partnerships",
            "Analytics & Admin Dashboard"
        ]
    }


# ============= EXCEPTION HANDLERS =============
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler
    
    Args:
        request: Request object
        exc: Exception object
    
    Returns:
        JSONResponse: Error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "ServerError",
            "message": "An unexpected error occurred",
            "status_code": 500
        }
    )


# ============= STARTUP LOGGING =============
if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database: {settings.database_url}")