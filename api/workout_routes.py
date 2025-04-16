"""
Workout plan API routes for workout tracking application.

This module defines the REST API endpoints for managing workout plans,
including generating, retrieving, and executing workout plans.
"""
from flask import Blueprint, request, jsonify, session
import google.generativeai as genai
import json
import time
from typing import Dict, List, Any, Optional
import logging

from modules.workout_extractor import WorkoutExtractor
from database.repository import WorkoutPlanRepository, UserRepository
from database.models import db

from config import GOOGLE_API_KEY

# Create Blueprint for workout routes
workout_bp = Blueprint('workout', __name__, url_prefix='/api/workout')

# Initialize Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize workout extractor
workout_extractor = WorkoutExtractor(GOOGLE_API_KEY)


@workout_bp.route('/generate', methods=['POST'])
def generate_workout_plan():
    """
    Generate a workout plan based on user profile data.
    
    Request JSON:
        {
            "user_profile": {
                "weight": 70,
                "height": 175,
                "gender": "male",
                "activity": "moderate",
                "goal": "strength",
                "intensity": "medium"
            },
            "additional_requirements": "optional specific requirements"
        }
        
    Returns:
        JSON response with generated workout plan.
    """
    data = request.json
    
    # Validate request data
    if not data or 'user_profile' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required user profile data'
        }), 400
    
    # Extract user profile data
    user_profile = data['user_profile']
    required_fields = ['weight', 'height', 'gender', 'activity', 'goal', 'intensity']
    
    for field in required_fields:
        if field not in user_profile:
            return jsonify({
                'success': False,
                'error': f'Missing required field: {field}'
            }), 400
    
    # Create prompt for AI
    prompt = create_workout_prompt(user_profile, data.get('additional_requirements'))
    
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
        if user_id:
            save_workout_plan_to_db(user_id, extracted_plan)
        
        return jsonify({
            'success': True,
            'workout_plan': extracted_plan,
            'raw_plan': raw_workout_plan
        })
    
    except Exception as e:
        logging.error(f"Error generating workout plan: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to generate workout plan: {str(e)}'
        }), 500


@workout_bp.route('/plans', methods=['GET'])
def get_workout_plans():
    """
    Get all workout plans for the current user.
    
    Returns:
        JSON response with user's workout plans.
    """
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not logged in'
        }), 401
    
    # Get workout plans from database
    plan_repo = WorkoutPlanRepository()
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
    
    return jsonify({
        'success': True,
        'plans': formatted_plans
    })


@workout_bp.route('/plans/<int:plan_id>', methods=['GET'])
def get_workout_plan(plan_id):
    """
    Get a specific workout plan by ID.
    
    Args:
        plan_id: ID of the workout plan to retrieve.
        
    Returns:
        JSON response with workout plan details.
    """
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not logged in'
        }), 401
    
    # Get workout plan from database
    plan_repo = WorkoutPlanRepository()
    plan_details = plan_repo.get_plan_with_days_and_exercises(plan_id)
    
    if not plan_details:
        return jsonify({
            'success': False,
            'error': f'Workout plan not found with ID: {plan_id}'
        }), 404
    
    # Check if plan belongs to current user
    plan = plan_repo.get_workout_plan(plan_id)
    if plan.user_id != user_id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to access this workout plan'
        }), 403
    
    return jsonify({
        'success': True,
        'plan': plan_details
    })


@workout_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
def delete_workout_plan(plan_id):
    """
    Delete a specific workout plan by ID.
    
    Args:
        plan_id: ID of the workout plan to delete.
        
    Returns:
        JSON response indicating success or failure.
    """
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not logged in'
        }), 401
    
    # Get workout plan from database
    plan_repo = WorkoutPlanRepository()
    plan = plan_repo.get_workout_plan(plan_id)
    
    if not plan:
        return jsonify({
            'success': False,
            'error': f'Workout plan not found with ID: {plan_id}'
        }), 404
    
    # Check if plan belongs to current user
    if plan.user_id != user_id:
        return jsonify({
            'success': False,
            'error': 'You do not have permission to delete this workout plan'
        }), 403
    
    # Delete the plan
    success = plan_repo.delete_workout_plan(plan_id)
    
    if not success:
        return jsonify({
            'success': False,
            'error': 'Failed to delete workout plan'
        }), 500
    
    return jsonify({
        'success': True,
        'message': f'Workout plan with ID {plan_id} deleted successfully'
    })


@workout_bp.route('/plans/<int:plan_id>/start', methods=['POST'])
def start_workout_plan(plan_id):
    """
    Start a workout session for a specific workout plan.
    
    Args:
        plan_id: ID of the workout plan to start.
        
    Returns:
        JSON response with workout plan details for execution.
    """
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not logged in'
        }), 401
    
    # Get workout plan from database
    plan_repo = WorkoutPlanRepository()
    plan_details = plan_repo.get_plan_with_days_and_exercises(plan_id)
    
    if not plan_details:
        return jsonify({
            'success': False,
            'error': f'Workout plan not found with ID: {plan_id}'
        }), 404
    
    # Store plan ID in session for tracking
    session['workout_plan_id'] = plan_id
    
    return jsonify({
        'success': True,
        'plan': plan_details,
        'message': f'Workout plan with ID {plan_id} started'
    })


@workout_bp.route('/current', methods=['GET'])
def get_current_workout():
    """
    Get the workout plan currently in session.
    
    Returns:
        JSON response with current workout plan.
    """
    # Check if there's a plan in session
    workout_plan = session.get('workout_plan_structured')
    
    if not workout_plan:
        # Check if there's a plan ID in session
        plan_id = session.get('workout_plan_id')
        if plan_id:
            # Get plan from database
            plan_repo = WorkoutPlanRepository()
            workout_plan = plan_repo.get_plan_with_days_and_exercises(plan_id)
    
    if not workout_plan:
        return jsonify({
            'success': False,
            'error': 'No active workout plan in session'
        }), 404
    
    return jsonify({
        'success': True,
        'workout_plan': workout_plan
    })


def create_workout_prompt(user_profile: Dict[str, Any], additional_requirements: Optional[str] = None) -> str:
    """
    Create an AI prompt to generate a personalized workout plan.
    
    Args:
        user_profile: Dictionary containing user profile data.
        additional_requirements: Optional specific requirements for the workout plan.
        
    Returns:
        String prompt for the AI model.
    """
    prompt = f"""
    You are a specialized workout plan generator. Create a strict 7-day workout plan based on the following information:
    - Weight: {user_profile.get('weight', 'Not provided')} kg
    - Height: {user_profile.get('height', 'Not provided')} cm
    - Gender: {user_profile.get('gender', 'Not provided')}
    - Current activity level: {user_profile.get('activity', 'Not provided')}
    - Fitness goal: {user_profile.get('goal', 'Not provided')}
    - Desired Workout Intensity: {user_profile.get('intensity', 'Not provided')} (amount of time can spend per week to workout)

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


def save_workout_plan_to_db(user_id: int, workout_plan: List[Dict[str, Any]]) -> Optional[int]:
    """
    Save a generated workout plan to the database.
    
    Args:
        user_id: ID of the user who owns this plan.
        workout_plan: Structured workout plan data.
        
    Returns:
        ID of the created workout plan or None if creation failed.
    """
    # Create workout plan
    plan_repo = WorkoutPlanRepository()
    
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