"""
Database models for the workout application.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for storing user data."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User profile data
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    gender = db.Column(db.String(20))
    activity_level = db.Column(db.String(50))
    fitness_goal = db.Column(db.String(100))
    workout_intensity = db.Column(db.String(50))
    
    # Relationships
    workout_plans = db.relationship('WorkoutPlan', backref='user', lazy=True)
    workout_sessions = db.relationship('WorkoutSession', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class WorkoutPlan(db.Model):
    """Model for storing generated workout plans."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    days = db.relationship('WorkoutDay', backref='workout_plan', lazy=True, 
                           cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WorkoutPlan {self.title}>'

class WorkoutDay(db.Model):
    """Model for storing workout days within a plan."""
    id = db.Column(db.Integer, primary_key=True)
    workout_plan_id = db.Column(db.Integer, db.ForeignKey('workout_plan.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    
    # Relationships
    exercises = db.relationship('Exercise', backref='workout_day', lazy=True, 
                                cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WorkoutDay {self.day_number} of Plan {self.workout_plan_id}>'

class Exercise(db.Model):
    """Model for storing exercises within a workout day."""
    id = db.Column(db.Integer, primary_key=True)
    workout_day_id = db.Column(db.Integer, db.ForeignKey('workout_day.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, default=1)
    reps = db.Column(db.Integer, nullable=False)
    is_timed = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Exercise {self.name}>'

class WorkoutSession(db.Model):
    """Model for storing completed workout sessions."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workout_plan_id = db.Column(db.Integer, db.ForeignKey('workout_plan.id'), nullable=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    
    # Relationships
    exercise_records = db.relationship('ExerciseRecord', backref='workout_session', lazy=True, 
                                      cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WorkoutSession {self.id} by User {self.user_id}>'

class ExerciseRecord(db.Model):
    """Model for storing exercise performance within a workout session."""
    id = db.Column(db.Integer, primary_key=True)
    workout_session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    reps_completed = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer)  # Duration in seconds for timed exercises
    
    # Relationships
    feedback_records = db.relationship('FeedbackRecord', backref='exercise_record', lazy=True, 
                                      cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ExerciseRecord {self.exercise_name} in Session {self.workout_session_id}>'

class FeedbackRecord(db.Model):
    """Model for storing feedback on exercise form."""
    id = db.Column(db.Integer, primary_key=True)
    exercise_record_id = db.Column(db.Integer, db.ForeignKey('exercise_record.id'), nullable=False)
    feedback_text = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Integer, default=1)  # How many times this feedback was given
    severity = db.Column(db.String(20))  # LOW, MEDIUM, HIGH
    
    def __repr__(self):
        return f'<FeedbackRecord "{self.feedback_text[:20]}..." for ExerciseRecord {self.exercise_record_id}>'