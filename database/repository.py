"""
Repository layer for database operations.
Provides abstraction over SQLAlchemy models and handles transaction management.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from database.models import (
    db, User, WorkoutPlan, WorkoutDay, Exercise, 
    WorkoutSession, ExerciseRecord, FeedbackRecord
)

class UserRepository:
    """Repository for User model operations."""
    
    @staticmethod
    def create_user(username: str, email: str, password_hash: str, **profile_data) -> Optional[User]:
        """Create a new user."""
        try:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                **profile_data
            )
            db.session.add(user)
            db.session.commit()
            return user
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username."""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def update_user_profile(user_id: int, **profile_data) -> Optional[User]:
        """Update user profile data."""
        user = User.query.get(user_id)
        if not user:
            return None
        
        try:
            for key, value in profile_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            db.session.commit()
            return user
        except SQLAlchemyError:
            db.session.rollback()
            return None

class WorkoutPlanRepository:
    """Repository for workout plan operations."""
    
    @staticmethod
    def create_workout_plan(user_id: int, title: str, description: str = None) -> Optional[WorkoutPlan]:
        """Create a new workout plan."""
        try:
            plan = WorkoutPlan(
                user_id=user_id,
                title=title,
                description=description
            )
            db.session.add(plan)
            db.session.commit()
            return plan
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def add_workout_day(plan_id: int, day_number: int, exercises: List[Dict[str, Any]]) -> Optional[WorkoutDay]:
        """Add a day to a workout plan with exercises."""
        try:
            day = WorkoutDay(
                workout_plan_id=plan_id,
                day_number=day_number
            )
            db.session.add(day)
            db.session.flush()  # Get the day ID
            
            for exercise_data in exercises:
                exercise = Exercise(
                    workout_day_id=day.id,
                    name=exercise_data.get('name'),
                    sets=exercise_data.get('sets', 1),
                    reps=exercise_data.get('reps'),
                    is_timed=exercise_data.get('is_timed', False)
                )
                db.session.add(exercise)
            
            db.session.commit()
            return day
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def get_workout_plan(plan_id: int) -> Optional[WorkoutPlan]:
        """Get a workout plan by ID."""
        return WorkoutPlan.query.get(plan_id)
    
    @staticmethod
    def get_user_workout_plans(user_id: int) -> List[WorkoutPlan]:
        """Get all workout plans for a user."""
        return WorkoutPlan.query.filter_by(user_id=user_id).order_by(WorkoutPlan.created_at.desc()).all()
    
    @staticmethod
    def get_plan_with_days_and_exercises(plan_id: int) -> Optional[Dict[str, Any]]:
        """Get a workout plan with all days and exercises."""
        plan = WorkoutPlan.query.get(plan_id)
        if not plan:
            return None
        
        days = WorkoutDay.query.filter_by(workout_plan_id=plan_id).order_by(WorkoutDay.day_number).all()
        result = {
            'id': plan.id,
            'title': plan.title,
            'description': plan.description,
            'created_at': plan.created_at,
            'days': []
        }
        
        for day in days:
            exercises = Exercise.query.filter_by(workout_day_id=day.id).all()
            day_data = {
                'day': f"Day {day.day_number}",
                'exercises': [
                    {
                        'name': ex.name,
                        'sets': ex.sets,
                        'reps': ex.reps,
                        'is_timed': ex.is_timed
                    } for ex in exercises
                ]
            }
            result['days'].append(day_data)
        
        return result
    
    @staticmethod
    def delete_workout_plan(plan_id: int) -> bool:
        """Delete a workout plan."""
        plan = WorkoutPlan.query.get(plan_id)
        if not plan:
            return False
        
        try:
            db.session.delete(plan)
            db.session.commit()
            return True
        except SQLAlchemyError:
            db.session.rollback()
            return False

class WorkoutSessionRepository:
    """Repository for workout session operations."""
    
    @staticmethod
    def create_session(user_id: int, workout_plan_id: int = None) -> Optional[WorkoutSession]:
        """Create a new workout session."""
        try:
            session = WorkoutSession(
                user_id=user_id,
                workout_plan_id=workout_plan_id,
                start_time=datetime.utcnow()
            )
            db.session.add(session)
            db.session.commit()
            return session
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def end_session(session_id: int) -> Optional[WorkoutSession]:
        """End a workout session."""
        session = WorkoutSession.query.get(session_id)
        if not session:
            return None
        
        try:
            session.end_time = datetime.utcnow()
            db.session.commit()
            return session
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def add_exercise_record(session_id: int, exercise_name: str, 
                           reps_completed: int, duration: int = None) -> Optional[ExerciseRecord]:
        """Add an exercise record to a session."""
        try:
            record = ExerciseRecord(
                workout_session_id=session_id,
                exercise_name=exercise_name,
                reps_completed=reps_completed,
                duration=duration
            )
            db.session.add(record)
            db.session.commit()
            return record
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def add_feedback_record(exercise_record_id: int, feedback_text: str, 
                           severity: str) -> Optional[FeedbackRecord]:
        """Add a feedback record to an exercise record."""
        # Check if this feedback already exists
        existing = FeedbackRecord.query.filter_by(
            exercise_record_id=exercise_record_id,
            feedback_text=feedback_text
        ).first()
        
        try:
            if existing:
                existing.frequency += 1
                db.session.commit()
                return existing
            else:
                record = FeedbackRecord(
                    exercise_record_id=exercise_record_id,
                    feedback_text=feedback_text,
                    severity=severity
                )
                db.session.add(record)
                db.session.commit()
                return record
        except SQLAlchemyError:
            db.session.rollback()
            return None
    
    @staticmethod
    def get_user_sessions(user_id: int, limit: int = 10) -> List[WorkoutSession]:
        """Get recent workout sessions for a user."""
        return WorkoutSession.query.filter_by(user_id=user_id).order_by(
            WorkoutSession.start_time.desc()).limit(limit).all()
    
    @staticmethod
    def get_session_with_records(session_id: int) -> Optional[Dict[str, Any]]:
        """Get a workout session with all exercise and feedback records."""
        session = WorkoutSession.query.get(session_id)
        if not session:
            return None
        
        exercise_records = ExerciseRecord.query.filter_by(workout_session_id=session_id).all()
        result = {
            'id': session.id,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'exercises': []
        }
        
        for record in exercise_records:
            feedback_records = FeedbackRecord.query.filter_by(exercise_record_id=record.id).all()
            exercise_data = {
                'name': record.exercise_name,
                'reps_completed': record.reps_completed,
                'duration': record.duration,
                'feedback': [
                    {
                        'text': fb.feedback_text,
                        'frequency': fb.frequency,
                        'severity': fb.severity
                    } for fb in feedback_records
                ]
            }
            result['exercises'].append(exercise_data)
        
        return result
    
    @staticmethod
    def get_common_feedback(user_id: int, period: str = 'month', exercise_name: str = None) -> List[Dict[str, Any]]:
        """
        Get common feedback for a user within a period.
        period: 'session', 'week', 'month'
        """
        # Implementation would include date filtering based on period
        # and potentially filtering by exercise_name
        # This is a simplified version
        
        query = db.session.query(
            FeedbackRecord.feedback_text,
            db.func.count(FeedbackRecord.id).label('count'),
            db.func.max(FeedbackRecord.severity).label('max_severity')
        )
        
        # Join with ExerciseRecord and WorkoutSession to filter by user_id
        query = query.join(
            ExerciseRecord, FeedbackRecord.exercise_record_id == ExerciseRecord.id
        ).join(
            WorkoutSession, ExerciseRecord.workout_session_id == WorkoutSession.id
        ).filter(
            WorkoutSession.user_id == user_id
        )
        
        # Add exercise filter if provided
        if exercise_name:
            query = query.filter(ExerciseRecord.exercise_name == exercise_name)
        
        # Group by feedback text and order by count
        results = query.group_by(FeedbackRecord.feedback_text).order_by(
            db.desc('count')
        ).limit(10).all()
        
        return [
            {
                'feedback': result[0],
                'count': result[1],
                'severity': result[2]
            } for result in results
        ]