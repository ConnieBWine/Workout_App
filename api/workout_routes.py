"""
Workout plan API routes for workout tracking application.

This module defines the REST API endpoints for managing workout plans,
including generating, retrieving, and executing workout plans.
"""
import time
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import google.generativeai as genai

from modules.workout_extractor import WorkoutExtractor
from database.repository import WorkoutPlanRepository, UserRepository
from database.db import get_db
from config import GOOGLE_API_KEY

# Create router
workout_router = APIRouter()

# Initialize Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize workout extractor
workout_extractor = WorkoutExtractor(GOOGLE_API_KEY)

# Pydantic models for request/response validation
class UserProfile(BaseModel):
    weight: float
    height: float
    gender: str
    activity: str
    goal: str
    intensity: str

class GenerateWorkoutRequest(BaseModel):
    user_profile: UserProfile
    additional_requirements: Optional[str] = None

class WorkoutPlanResponse(BaseModel):
    success: bool
    workout_plan: Optional[Any] = None
    raw_plan: Optional[str] = None
    error: Optional[str] = None

class WorkoutPlansResponse(BaseModel):
    success: bool
    plans: List[Dict[str, Any]] = []
    error: Optional[str] = None

class WorkoutPlanDetailResponse(BaseModel):
    success: bool
    plan: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class StartWorkoutResponse(BaseModel):
    success: bool
    plan: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None

@workout_router.post("/generate", response_model=WorkoutPlanResponse)
async def generate_workout_plan(
    data: GenerateWorkoutRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Generate a workout plan based on user profile data.
    """
    session = request.session
    
    # Create prompt for AI
    prompt = create_workout_prompt(data.user_profile, data.additional_requirements)
    
    try:
        # Generate workout plan
        logging.info(f"Sending prompt to GenAI: {prompt[:100]}...")
        response = model.generate_content(prompt)
        raw_workout_plan = response.text
        
        # Extract structured workout plan
        extracted_plan = workout_extractor.extract_workout_plan(raw_workout_plan)
        
        # Store in session
        session['workout_plan_raw'] = raw_workout_plan
        session['workout_plan_structured'] = extracted_plan
        
        # Save to database if user is logged in
        user_id = session.get('user_id')
        saved_plan_id = None
        if user_id:
            saved_plan_id = save_workout_plan_to_db(user_id, extracted_plan, db)
        
        return WorkoutPlanResponse(
            success=True,
            workout_plan=extracted_plan,
            raw_plan=raw_workout_plan
        )
    
    except Exception as e:
        logging.error(f"Error generating workout plan: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f'Failed to generate workout plan: {str(e)}'
        )

@workout_router.get("/plans", response_model=WorkoutPlansResponse)
async def get_workout_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get all workout plans for the current user.
    """
    session = request.session
    
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not logged in"
        )
    
    # Get workout plans from database
    plan_repo = WorkoutPlanRepository(db)
    plans = plan_repo.get_user_workout_plans(user_id)
    
    # Format plans for API response
    formatted_plans = []
    for plan in plans:
        formatted_plan = {
            'id': plan.id,
            'title': plan.title,
            'description': plan.description,
            'created_at': plan.created_at.isoformat()
        }
        
        # Get detailed plan structure
        plan_details = plan_repo.get_plan_with_days_and_exercises(plan.id)
        if plan_details:
            formatted_plan['days'] = plan_details['days']
        
        formatted_plans.append(formatted_plan)
    
    return WorkoutPlansResponse(
        success=True,
        plans=formatted_plans
    )

@workout_router.get("/plans/{plan_id}", response_model=WorkoutPlanDetailResponse)
async def get_workout_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get a specific workout plan by ID.
    """
    session = request.session
    
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not logged in"
        )
    
    # Get workout plan from database
    plan_repo = WorkoutPlanRepository(db)
    plan_details = plan_repo.get_plan_with_days_and_exercises(plan_id)
    
    if not plan_details:
        raise HTTPException(
            status_code=404,
            detail=f'Workout plan not found with ID: {plan_id}'
        )
    
    # Check if plan belongs to current user
    plan = plan_repo.get_workout_plan(plan_id)
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail='You do not have permission to access this workout plan'
        )
    
    return WorkoutPlanDetailResponse(
        success=True,
        plan=plan_details
    )

@workout_router.delete("/plans/{plan_id}")
async def delete_workout_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Delete a specific workout plan by ID.
    """
    session = request.session
    
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not logged in"
        )
    
    # Get workout plan from database
    plan_repo = WorkoutPlanRepository(db)
    plan = plan_repo.get_workout_plan(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f'Workout plan not found with ID: {plan_id}'
        )
    
    # Check if plan belongs to current user
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail='You do not have permission to delete this workout plan'
        )
    
    # Delete the plan
    success = plan_repo.delete_workout_plan(plan_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail='Failed to delete workout plan'
        )
    
    return {
        'success': True,
        'message': f'Workout plan with ID {plan_id} deleted successfully'
    }

@workout_router.post("/plans/{plan_id}/start", response_model=StartWorkoutResponse)
async def start_workout_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Start a workout session for a specific workout plan.
    """
    session = request.session
    
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not logged in"
        )
    
    # Get workout plan from database
    plan_repo = WorkoutPlanRepository(db)
    plan_details = plan_repo.get_plan_with_days_and_exercises(plan_id)
    
    if not plan_details:
        raise HTTPException(
            status_code=404,
            detail=f'Workout plan not found with ID: {plan_id}'
        )
    
    # Store plan ID in session for tracking
    session['workout_plan_id'] = plan_id
    
    return StartWorkoutResponse(
        success=True,
        plan=plan_details,
        message=f'Workout plan with ID {plan_id} started'
    )

@workout_router.get("/current", response_model=WorkoutPlanDetailResponse)
async def get_current_workout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get the workout plan currently in session.
    """
    session = request.session
    
    # Check if there's a plan in session
    workout_plan = session.get('workout_plan_structured')
    
    if not workout_plan:
        # Check if there's a plan ID in session
        plan_id = session.get('workout_plan_id')
        if plan_id:
            # Get plan from database
            plan_repo = WorkoutPlanRepository(db)
            workout_plan = plan_repo.get_plan_with_days_and_exercises(plan_id)
    
    if not workout_plan:
        raise HTTPException(
            status_code=404,
            detail='No active workout plan in session'
        )
    
    return WorkoutPlanDetailResponse(
        success=True,
        plan=workout_plan
    )

def create_workout_prompt(user_profile: UserProfile, additional_requirements: Optional[str] = None) -> str:
    """
    Create an AI prompt to generate a personalized workout plan.
    
    Args:
        user_profile: User profile data.
        additional_requirements: Optional specific requirements for the workout plan.
        
    Returns:
        String prompt for the AI model.
    """
    prompt = f"""
    You are a specialized workout plan generator. Create a strict 7-day workout plan based on the following information:
    - Weight: {user_profile.weight} kg
    - Height: {user_profile.height} cm
    - Gender: {user_profile.gender}
    - Current activity level: {user_profile.activity}
    - Fitness goal: {user_profile.goal}
    - Desired Workout Intensity: {user_profile.intensity} (amount of time can spend per week to workout)

    Adhere to these rules strictly:
    1. Provide exactly 7 days of workouts, labeled Day 1 through Day 7.
    2. Each day must have 3-5 exercises.
    3. Use only the following exercises:
    Reps-based: curl, squat, lunge, pushup, shoulder press
    Duration-based: plank, jumping jack, jump rope, knee tap, mountain climber
    4. Format each exercise as follows:
    Reps-based: [Exercise Name]: [Sets] x [Reps]
    Duration-based: [Exercise Name]: [Duration] seconds
    5. Do not include any introductions, explanations, or dietary advice.
    6. Use the exact exercise names provided, with correct spelling.
    """
    
    if additional_requirements:
        prompt += f"\nAdditional requirements: {additional_requirements}"
    
    prompt += """
    Example of correct formatting:
    Day 1:
    Jumping Jack: 30 seconds
    Pushup: 3 x 10
    Plank: 60 seconds
    Squat: 3 x 15
    Mountain Climber: 45 seconds

    Your response must follow this exact structure for all 7 days. DO NOT deviate from this format or include any additional information.

    Begin the 7-day workout plan NOW:
    """
    
    return prompt

def save_workout_plan_to_db(user_id: int, workout_plan: List[Dict[str, Any]], db: Session) -> Optional[int]:
    """
    Save a generated workout plan to the database.
    
    Args:
        user_id: ID of the user who owns this plan.
        workout_plan: Structured workout plan data.
        db: Database session.
        
    Returns:
        ID of the created workout plan or None if creation failed.
    """
    # Create workout plan
    plan_repo = WorkoutPlanRepository(db)
    
    # Generate title based on workout focus
    exercise_counts = {}
    for day in workout_plan:
        for exercise in day.get('exercises', []):
            exercise_name = exercise.get('name', '').lower()
            if exercise_name in exercise_counts:
                exercise_counts[exercise_name] += 1
            else:
                exercise_counts[exercise_name] = 1
    
    # Find the most common exercise type
    most_common_exercise = max(exercise_counts.items(), key=lambda x: x[1])[0] if exercise_counts else "general"
    
    # Create title and description
    title = f"{most_common_exercise.title()}-focused Workout Plan"
    description = f"7-day workout plan generated on {time.strftime('%Y-%m-%d')}"
    
    # Create plan in database
    plan = plan_repo.create_workout_plan(user_id, title, description)
    if not plan:
        return None
    
    # Add days and exercises
    for i, day in enumerate(workout_plan, 1):
        exercises = day.get('exercises', [])
        plan_repo.add_workout_day(plan.id, i, exercises)
    
    return plan.id