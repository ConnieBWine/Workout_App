"""
Exercise API routes for workout tracking application.

This module defines the REST API endpoints for managing exercise tracking,
including starting exercises, retrieving exercise data, and managing workout sessions.
"""
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from modules.video_processor import VideoProcessor, ExerciseType
from database.repository import WorkoutSessionRepository
from database.db import get_db

# Create router
exercise_router = APIRouter()

# Global video processor instance (shared across routes)
video_processor = VideoProcessor()

# Pydantic models for request/response validation
class StartExerciseRequest(BaseModel):
    exercise: str
    is_timed: bool = False
    target_reps: Optional[int] = None
    target_duration: Optional[int] = None

class ExerciseDataResponse(BaseModel):
    current_exercise: Optional[str] = None
    exercise_state: Optional[str] = None
    rep_count: int = 0
    time_accumulated: float = 0
    feedback: List[str] = []
    is_timed_exercise: bool = False
    progress: float = 0
    target_reps: Optional[int] = None
    target_duration: Optional[int] = None
    detailed_metrics: Dict[str, Any] = {}

class ExerciseFeedback(BaseModel):
    text: str
    count: int
    severity: Optional[str] = None

class CommonFeedbackResponse(BaseModel):
    success: bool
    feedback: List[Dict[str, Any]] = []

class ExerciseHistoryResponse(BaseModel):
    success: bool
    history: List[Dict[str, Any]] = []

class ExerciseStatsResponse(BaseModel):
    success: bool
    statistics: Dict[str, Any] = {}

class ExerciseStopResponse(BaseModel):
    success: bool
    exercise: str
    duration: float
    rep_count: int
    time_accumulated: float
    statistics: Dict[str, Any]

@exercise_router.post("/start", response_model=Dict[str, Any])
async def start_exercise(
    data: StartExerciseRequest, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Start a specific exercise for tracking.
    """
    session = request.session
    
    # Set current exercise in video processor
    success = video_processor.set_current_exercise(data.exercise, data.is_timed)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid exercise type: {data.exercise}"
        )
    
    # Store exercise parameters in session
    session['current_exercise'] = {
        'name': data.exercise,
        'is_timed': data.is_timed,
        'target_reps': data.target_reps,
        'target_duration': data.target_duration,
        'start_time': time.time()
    }
    
    # Start a new workout session in database if user is logged in
    user_id = session.get('user_id')
    if user_id:
        # Check if there's a workout plan ID in session
        workout_plan_id = session.get('workout_plan_id')
        
        # Create new workout session
        session_repo = WorkoutSessionRepository(db)
        workout_session = session_repo.create_session(user_id, workout_plan_id)
        
        if workout_session:
            session['workout_session_id'] = workout_session.id
    
    return {
        'success': True,
        'message': f'Started {data.exercise} exercise tracking',
        'is_timed': data.is_timed
    }

@exercise_router.post("/stop", response_model=ExerciseStopResponse)
async def stop_exercise(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stop the current exercise tracking.
    """
    session = request.session
    
    # Check if there's an active exercise
    if 'current_exercise' not in session:
        raise HTTPException(
            status_code=400, 
            detail="No active exercise to stop"
        )
    
    # Get current exercise data
    current_exercise = session.pop('current_exercise', {})
    exercise_name = current_exercise.get('name')
    start_time = current_exercise.get('start_time', time.time())
    duration = time.time() - start_time
    
    # Get final exercise data from video processor
    exercise_data = video_processor.exercise_data
    rep_count = exercise_data.get('rep_count', 0)
    time_accumulated = exercise_data.get('time_accumulated', 0)
    
    # Record exercise in database if user is logged in
    user_id = session.get('user_id')
    workout_session_id = session.get('workout_session_id')
    
    if user_id and workout_session_id:
        session_repo = WorkoutSessionRepository(db)
        
        # Add exercise record
        exercise_record = session_repo.add_exercise_record(
            workout_session_id,
            exercise_name,
            rep_count,
            int(time_accumulated) if current_exercise.get('is_timed') else None
        )
        
        # Add feedback records if there were any
        if exercise_record:
            for feedback_item in video_processor.session_stats.get('feedback_frequency', {}):
                count = video_processor.session_stats['feedback_frequency'][feedback_item]
                # Only record significant feedback (occurred multiple times)
                if count >= 2:
                    severity = "HIGH" if count >= 5 else "MEDIUM" if count >= 3 else "LOW"
                    session_repo.add_feedback_record(
                        exercise_record.id,
                        feedback_item,
                        severity
                    )
    
    # Get session statistics before resetting
    statistics = video_processor.get_session_statistics()
    
    # Reset video processor state
    video_processor.reset_session()
    
    return {
        'success': True,
        'exercise': exercise_name,
        'duration': duration,
        'rep_count': rep_count,
        'time_accumulated': time_accumulated,
        'statistics': statistics
    }

@exercise_router.get("/data", response_model=ExerciseDataResponse)
async def get_exercise_data(request: Request):
    """
    Get current exercise data.
    """
    session = request.session
    
    # Get data from video processor
    exercise_data = video_processor.exercise_data
    
    # Add information from session
    current_exercise = session.get('current_exercise', {})
    target_reps = current_exercise.get('target_reps')
    target_duration = current_exercise.get('target_duration')
    
    # Calculate progress percentage
    progress = 0
    if current_exercise.get('is_timed') and target_duration:
        time_accumulated = exercise_data.get('time_accumulated', 0)
        progress = min(100, (time_accumulated / target_duration) * 100)
    elif target_reps:
        rep_count = exercise_data.get('rep_count', 0)
        progress = min(100, (rep_count / target_reps) * 100)
    
    # Add progress to response
    exercise_data['progress'] = progress
    exercise_data['target_reps'] = target_reps
    exercise_data['target_duration'] = target_duration
    
    return exercise_data

@exercise_router.get("/stats", response_model=ExerciseStatsResponse)
async def get_exercise_stats():
    """
    Get comprehensive exercise statistics for the current session.
    """
    # Get statistics from video processor
    statistics = video_processor.get_session_statistics()
    
    return {
        'success': True,
        'statistics': statistics
    }

@exercise_router.get("/history", response_model=ExerciseHistoryResponse)
async def get_exercise_history(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get exercise history for the current user.
    """
    session = request.session
    
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not logged in"
        )
    
    # Get exercise history from database
    session_repo = WorkoutSessionRepository(db)
    workout_sessions = session_repo.get_user_sessions(user_id)
    
    # Process sessions into a suitable format for frontend
    history = []
    for workout_session in workout_sessions:
        session_data = session_repo.get_session_with_records(workout_session.id)
        if session_data:
            history.append(session_data)
    
    return {
        'success': True,
        'history': history
    }

@exercise_router.get("/common_feedback", response_model=CommonFeedbackResponse)
async def get_common_feedback(
    exercise: Optional[str] = None,
    period: str = "month",
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get common feedback for a specific exercise or all exercises.
    
    Query parameters:
        exercise: Optional exercise name to filter feedback
        period: Optional period ('session', 'week', 'month')
    """
    session = request.session
    
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not logged in"
        )
    
    # Get common feedback from database
    session_repo = WorkoutSessionRepository(db)
    feedback_items = session_repo.get_common_feedback(user_id, period, exercise)
    
    return {
        'success': True,
        'feedback': feedback_items
    }