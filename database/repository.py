"""
Repository layer for database operations.
Provides abstraction over SQLAlchemy models and handles transaction management.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database.models import (
    User, WorkoutPlan, WorkoutDay, Exercise, 
    WorkoutSession, ExerciseRecord, FeedbackRecord
)

class UserRepository:
    """Repository for User model operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, username: str, email: str, password_hash: str, **profile_data) -> Optional[User]:
        """Create a new user."""
        try:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                **profile_data
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def update_user_profile(self, user_id: int, **profile_data) -> Optional[User]:
        """Update user profile data."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        try:
            for key, value in profile_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None

class WorkoutPlanRepository:
    """Repository for workout plan operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_workout_plan(self, user_id: int, title: str, description: str = None) -> Optional[WorkoutPlan]:
        """Create a new workout plan."""
        try:
            plan = WorkoutPlan(
                user_id=user_id,
                title=title,
                description=description
            )
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            return plan
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def add_workout_day(self, plan_id: int, day_number: int, exercises: List[Dict[str, Any]]) -> Optional[WorkoutDay]:
        """Add a day to a workout plan with exercises."""
        try:
            day = WorkoutDay(
                workout_plan_id=plan_id,
                day_number=day_number
            )
            self.db.add(day)
            self.db.flush()  # Get the day ID
            
            for exercise_data in exercises:
                exercise = Exercise(
                    workout_day_id=day.id,
                    name=exercise_data.get('name'),
                    sets=exercise_data.get('sets', 1),
                    reps=exercise_data.get('reps'),
                    is_timed=exercise_data.get('is_timed', False)
                )
                self.db.add(exercise)
            
            self.db.commit()
            self.db.refresh(day)
            return day
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def get_workout_plan(self, plan_id: int) -> Optional[WorkoutPlan]:
        """Get a workout plan by ID."""
        return self.db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
    
    def get_user_workout_plans(self, user_id: int) -> List[WorkoutPlan]:
        """Get all workout plans for a user."""
        return self.db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).order_by(desc(WorkoutPlan.created_at)).all()
    
    def get_plan_with_days_and_exercises(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get a workout plan with all days and exercises."""
        plan = self.db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
        if not plan:
            return None
        
        days = self.db.query(WorkoutDay).filter(WorkoutDay.workout_plan_id == plan_id).order_by(WorkoutDay.day_number).all()
        result = {
            'id': plan.id,
            'title': plan.title,
            'description': plan.description,
            'created_at': plan.created_at,
            'days': []
        }
        
        for day in days:
            exercises = self.db.query(Exercise).filter(Exercise.workout_day_id == day.id).all()
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
    
    def delete_workout_plan(self, plan_id: int) -> bool:
        """Delete a workout plan."""
        plan = self.db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
        if not plan:
            return False
        
        try:
            self.db.delete(plan)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False

class WorkoutSessionRepository:
    """Repository for workout session operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, user_id: int, workout_plan_id: int = None) -> Optional[WorkoutSession]:
        """Create a new workout session."""
        try:
            session = WorkoutSession(
                user_id=user_id,
                workout_plan_id=workout_plan_id,
                start_time=datetime.utcnow()
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def end_session(self, session_id: int) -> Optional[WorkoutSession]:
        """End a workout session."""
        session = self.db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
        if not session:
            return None
        
        try:
            session.end_time = datetime.utcnow()
            self.db.commit()
            self.db.refresh(session)
            return session
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def add_exercise_record(self, session_id: int, exercise_name: str, 
                           reps_completed: int, duration: int = None) -> Optional[ExerciseRecord]:
        """Add an exercise record to a session."""
        try:
            record = ExerciseRecord(
                workout_session_id=session_id,
                exercise_name=exercise_name,
                reps_completed=reps_completed,
                duration=duration
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def add_feedback_record(self, exercise_record_id: int, feedback_text: str, 
                           severity: str) -> Optional[FeedbackRecord]:
        """Add a feedback record to an exercise record."""
        # Check if this feedback already exists
        existing = self.db.query(FeedbackRecord).filter(
            FeedbackRecord.exercise_record_id == exercise_record_id,
            FeedbackRecord.feedback_text == feedback_text
        ).first()
        
        try:
            if existing:
                existing.frequency += 1
                self.db.commit()
                self.db.refresh(existing)
                return existing
            else:
                record = FeedbackRecord(
                    exercise_record_id=exercise_record_id,
                    feedback_text=feedback_text,
                    severity=severity
                )
                self.db.add(record)
                self.db.commit()
                self.db.refresh(record)
                return record
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[WorkoutSession]:
        """Get recent workout sessions for a user."""
        return self.db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id
        ).order_by(desc(WorkoutSession.start_time)).limit(limit).all()
    
    def get_session_with_records(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a workout session with all exercise and feedback records."""
        session = self.db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
        if not session:
            return None
        
        exercise_records = self.db.query(ExerciseRecord).filter(
            ExerciseRecord.workout_session_id == session_id
        ).all()
        
        result = {
            'id': session.id,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'exercises': []
        }
        
        for record in exercise_records:
            feedback_records = self.db.query(FeedbackRecord).filter(
                FeedbackRecord.exercise_record_id == record.id
            ).all()
            
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
    
    def get_common_feedback(self, user_id: int, period: str = 'month', exercise_name: str = None) -> List[Dict[str, Any]]:
        """
        Get common feedback for a user within a period.
        period: 'session', 'week', 'month'
        """
        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'session':
            # Get the latest session
            latest_session = self.db.query(WorkoutSession).filter(
                WorkoutSession.user_id == user_id
            ).order_by(desc(WorkoutSession.start_time)).first()
            
            if not latest_session:
                return []
            
            # Get feedback from just this session
            session_records = self.db.query(ExerciseRecord).filter(
                ExerciseRecord.workout_session_id == latest_session.id
            ).all()
            
            record_ids = [record.id for record in session_records]
            if not record_ids:
                return []
            
            query = self.db.query(
                FeedbackRecord.feedback_text,
                func.count(FeedbackRecord.id).label('count'),
                func.max(FeedbackRecord.severity).label('max_severity')
            ).filter(
                FeedbackRecord.exercise_record_id.in_(record_ids)
            )
            
            if exercise_name:
                # First get exercise record IDs for the specified exercise
                exercise_record_ids = [
                    record.id for record in session_records
                    if record.exercise_name == exercise_name
                ]
                
                if not exercise_record_ids:
                    return []
                
                query = query.filter(
                    FeedbackRecord.exercise_record_id.in_(exercise_record_ids)
                )
            
            # Group by feedback text and order by count
            results = query.group_by(FeedbackRecord.feedback_text).order_by(
                desc('count')
            ).limit(10).all()
            
            return [
                {
                    'feedback': result.feedback_text,
                    'count': result.count,
                    'severity': result.max_severity
                } for result in results
            ]
        else:
            # Default to all time
            start_date = datetime(2000, 1, 1)
        
        # Query for session IDs in the date range
        if period != 'session':
            session_ids = [
                session.id for session in self.db.query(WorkoutSession).filter(
                    WorkoutSession.user_id == user_id,
                    WorkoutSession.start_time >= start_date,
                    WorkoutSession.start_time <= end_date
                ).all()
            ]
            
            if not session_ids:
                return []
            
            # Query for exercise record IDs
            query = self.db.query(
                FeedbackRecord.feedback_text,
                func.count(FeedbackRecord.id).label('count'),
                func.max(FeedbackRecord.severity).label('max_severity')
            )
            
            # Join with ExerciseRecord to filter by session IDs
            query = query.join(
                ExerciseRecord, FeedbackRecord.exercise_record_id == ExerciseRecord.id
            ).filter(
                ExerciseRecord.workout_session_id.in_(session_ids)
            )
            
            # Add exercise filter if provided
            if exercise_name:
                query = query.filter(ExerciseRecord.exercise_name == exercise_name)
            
            # Group by feedback text and order by count
            results = query.group_by(FeedbackRecord.feedback_text).order_by(
                desc('count')
            ).limit(10).all()
            
            return [
                {
                    'feedback': result.feedback_text,
                    'count': result.count,
                    'severity': result.max_severity
                } for result in results
            ]