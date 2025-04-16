"""
Main FastAPI application for workout tracking and analysis system.

This module initializes and configures the FastAPI application,
registers all routers, sets up database connections,
and provides the entry point for running the application.
"""
import os
import logging
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import google.generativeai as genai

# Import configuration
from config import (
    SECRET_KEY, DEBUG, DATABASE_URI, 
    GOOGLE_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT
)

# Import database models
from database.db import engine, get_db
from database.models import Base, User

# Import API routers
from api.exercise_routes import exercise_router
from api.video_routes import video_router
from api.workout_routes import workout_router

# Import video processing module
from modules.video_processor import VideoProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FitTrack API",
    description="API for workout tracking with pose detection",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=3600,  # 1 hour
)

# Create tables
Base.metadata.create_all(bind=engine)

# Configure Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)

# Create shared video processor instance
video_processor = VideoProcessor()

# Mount static files
app.mount("/static", StaticFiles(directory="static/build"), name="static")
templates = Jinja2Templates(directory="static/build")

# Include routers
app.include_router(exercise_router, prefix="/api/exercise", tags=["exercises"])
app.include_router(video_router, prefix="/api/video", tags=["video"])
app.include_router(workout_router, prefix="/api/workout", tags=["workouts"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the React frontend."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'version': '1.0.0'
    }

@app.get("/api/user/profile")
async def get_user_profile(request: Request):
    """Get user profile data from session."""
    session = request.session
    user_profile = session.get('user_profile', {})
    return user_profile

@app.post("/api/user/profile")
async def update_user_profile(profile_data: Dict[str, Any], request: Request):
    """Update user profile data."""
    session = request.session
    session['user_profile'] = profile_data
    return {
        'success': True,
        'message': 'Profile updated successfully'
    }

@app.post("/api/session/clear")
async def clear_session(request: Request):
    """Clear the session data."""
    request.session.clear()
    return {
        'success': True,
        'message': 'Session cleared'
    }

@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    """Handle 404 errors by serving React frontend."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.exception_handler(500)
async def server_error(request: Request, exc: HTTPException):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={
            'success': False,
            'error': 'Internal server error',
            'message': str(exc)
        }
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Additional startup code can go here
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    # Stop video processing
    from api.video_routes import stop_frame_processing
    stop_frame_processing()
    logger.info("Application shutting down")

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 5000))
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port, 
        reload=DEBUG
    )