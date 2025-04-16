"""
Exercise API routes for workout tracking application.

This module defines the REST API endpoints for managing exercise tracking,
including starting exercises, retrieving exercise data, and managing workout sessions.
"""
from flask import Blueprint, request, jsonify, session
from typing import Dict, Any
import time
from modules.video_processor import VideoProcessor, ExerciseType
from database.repository import WorkoutSessionRepository, ExerciseRecord
from database.models import db

# Create Blueprint for exercise routes
exercise_bp = Blueprint('exercise', __name__, url_prefix='/api/exercise')

# Global video processor instance (shared across routes)
video_processor = None


@exercise_bp.before_app_first_request
def initialize_video_processor():
    """Initialize the video processor on first request."""
    global video_processor
    if video_processor is None:
        video_processor = VideoProcessor()


@exercise_bp.route('/start', methods=['POST'])
def start_exercise():
    """
    Start a specific exercise for tracking.
    
    Request JSON:
        {
            "exercise": "exercise_name",
            "is_timed": false,  // Optional, default is false
            "target_reps": 10,  // Optional
            "target_duration": 60  // Optional, for timed exercises (seconds)
        }
        
    Returns:
        JSON response indicating success or failure.
    """
    global video_processor
    data = request.json
    
    # Validate request data
    if not data or 'exercise' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required fields'
        }), 400
    
    exercise_name = data['exercise']
    is_timed = data.get('is_timed', False)
    
    # Optional parameters
    target_reps = data.get('target_reps')
    target_duration = data.get('target_duration')
    
    # Set current exercise in video processor
    success = video_processor.set_current_exercise(exercise_name, is_timed)
    
    if not success:
        return jsonify({
            'success': False,
            'error': f'Invalid exercise type: {exercise_name}'
        }), 400
    
    # Store exercise parameters in session
    session['current_exercise'] = {
        'name': exercise_name,
        'is_timed': is_timed,
        'target_reps': target_reps,
        'target_duration': target_duration,
        'start_time': time.time()
    }
    
    # Start a new workout session in database if user is logged in
    user_id = session.get('user_id')
    if user_id:
        # Check if there's a workout plan ID in session
        workout_plan_id = session.get('workout_plan_id')
        
        # Create new workout session
        session_repo = WorkoutSessionRepository()
        workout_session = session_repo.create_session(user_id, workout_plan_id)
        
        if workout_session:
            session['workout_session_id'] = workout_session.id
    
    return jsonify({
        'success': True,
        'message': f'Started {exercise_name} exercise tracking',
        'is_timed': is_timed
    })


@exercise_bp.route('/stop', methods=['POST'])
def stop_exercise():
    """
    Stop the current exercise tracking.
    
    Returns:
        JSON response with exercise statistics.
    """
    global video_processor
    
    # Check if there's an active exercise
    if 'current_exercise' not in session:
        return jsonify({
            'success': False,
            'error': 'No active exercise to stop'
        }), 400
    
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
        session_repo = WorkoutSessionRepository()
        
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
    
    return jsonify({
        'success': True,
        'exercise': exercise_name,
        'duration': duration,
        'rep_count': rep_count,
        'time_accumulated': time_accumulated,
        'statistics': statistics
    })


@exercise_bp.route('/data', methods=['GET'])
def get_exercise_data():
    """
    Get current exercise data.
    
    Returns:
        JSON response with current exercise tracking data.
    """
    global video_processor
    
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
    
    return jsonify(exercise_data)


@exercise_bp.route('/stats', methods=['GET'])
def get_exercise_stats():
    """
    Get comprehensive exercise statistics for the current session.
    
    Returns:
        JSON response with detailed exercise statistics.
    """
    global video_processor
    
    # Get statistics from video processor
    statistics = video_processor.get_session_statistics()
    
    return jsonify(statistics)


@exercise_bp.route('/history', methods=['GET'])
def get_exercise_history():
    """
    Get exercise history for the current user.
    
    Returns:
        JSON response with exercise history.
    """
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not logged in'
        }), 401
    
    # Get exercise history from database
    session_repo = WorkoutSessionRepository()
    workout_sessions = session_repo.get_user_sessions(user_id)
    
    # Process sessions into a suitable format for frontend
    history = []
    for workout_session in workout_sessions:
        session_data = session_repo.get_session_with_records(workout_session.id)
        if session_data:
            history.append(session_data)
    
    return jsonify({
        'success': True,
        'history': history
    })


@exercise_bp.route('/common_feedback', methods=['GET'])
def get_common_feedback():
    """
    Get common feedback for a specific exercise or all exercises.
    
    Query parameters:
        exercise: Optional exercise name to filter feedback
        period: Optional period ('session', 'week', 'month')
        
    Returns:
        JSON response with common feedback items.
    """
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User not logged in'
        }), 401
    
    # Get query parameters
    exercise = request.args.get('exercise')
    period = request.args.get('period', 'month')
    
    # Get common feedback from database
    session_repo = WorkoutSessionRepository()
    feedback_items = session_repo.get_common_feedback(user_id, period, exercise)
    
    return jsonify({
        'success': True,
        'feedback': feedback_items
    })