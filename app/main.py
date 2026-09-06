# ============================================================================
# EventAI Backend - Main Application
# ============================================================================
# File: backend/app/main.py
# Purpose: FastAPI application setup with CORS configuration
# Status: Production-Ready ✅

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import init_db
from app.routes import (
    auth, users, speakers, sessions, resources, ratings,
    announcements, social, leaderboard, badges, challenges,
    learning_paths, engagement, partners, analytics, admin
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="EventAI API",
    description="Enterprise Event Management Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================================
# CORS Configuration - CRITICAL FOR FRONTEND CONNECTION
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://event-ai-frontend-ravirajapanthulu-5771.vercel.app",
        "https://eventai.vercel.app",
        "*"  # Allow all (can be restricted in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600
)

# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting EventAI API...")
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down EventAI API...")

# ============================================================================
# Health Check & Root Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "EventAI API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "EventAI API"
    }

@app.get("/api/v1/health")
async def api_health_check():
    return {
        "status": "healthy",
        "service": "EventAI API",
        "version": "1.0.0"
    }

# ============================================================================
# Include All Route Routers
# ============================================================================

# Auth Routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# User Routes
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

# Speaker Routes
app.include_router(speakers.router, prefix="/api/v1/speakers", tags=["Speakers"])

# Session Routes
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])

# Resource Routes
app.include_router(resources.router, prefix="/api/v1/resources", tags=["Resources"])

# Rating Routes
app.include_router(ratings.router, prefix="/api/v1/ratings", tags=["Ratings"])

# Announcement Routes
app.include_router(announcements.router, prefix="/api/v1/announcements", tags=["Announcements"])

# Social Routes
app.include_router(social.router, prefix="/api/v1/social", tags=["Social"])

# Leaderboard Routes
app.include_router(leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"])

# Badge Routes
app.include_router(badges.router, prefix="/api/v1/badges", tags=["Badges"])

# Challenge Routes
app.include_router(challenges.router, prefix="/api/v1/challenges", tags=["Challenges"])

# Learning Paths Routes
app.include_router(learning_paths.router, prefix="/api/v1/learning-paths", tags=["Learning Paths"])

# Engagement Routes
app.include_router(engagement.router, prefix="/api/v1/engagement", tags=["Engagement"])

# Partner Routes
app.include_router(partners.router, prefix="/api/v1/partners", tags=["Partners"])

# Analytics Routes
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

# Admin Routes
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )