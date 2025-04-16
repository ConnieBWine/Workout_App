"""
Database models for the workout application.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database.db import Base

class User(Base):
    """User model for storing user data."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # User profile data
    weight = Column(Float)
    height = Column(Float)
    gender = Column(String(20))
    activity_level = Column(String(50))
    fitness_goal = Column(String(100))
    workout_intensity = Column(String(50))
    
    # Relationships
    workout_plans = relationship("WorkoutPlan", back_populates="user")
    workout_sessions = relationship("WorkoutSession", back_populates="user")

    def __repr__(self):
        return f'<User {self.username}>'

class WorkoutPlan(Base):
    """Model for storing generated workout plans."""
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="workout_plans")
    days = relationship("WorkoutDay", back_populates="workout_plan", cascade="all, delete-orphan")
    sessions = relationship("WorkoutSession", back_populates="workout_plan")
    
    def __repr__(self):
        return f'<WorkoutPlan {self.title}>'

class WorkoutDay(Base):
    """Model for storing workout days within a plan."""
    __tablename__ = "workout_days"

    id = Column(Integer, primary_key=True, index=True)
    workout_plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    
    # Relationships
    workout_plan = relationship("WorkoutPlan", back_populates="days")
    exercises = relationship("Exercise", back_populates="workout_day", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<WorkoutDay {self.day_number} of Plan {self.workout_plan_id}>'

class Exercise(Base):
    """Model for storing exercises within a workout day."""
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    workout_day_id = Column(Integer, ForeignKey("workout_days.id"), nullable=False)
    name = Column(String(100), nullable=False)
    sets = Column(Integer, default=1)
    reps = Column(Integer, nullable=False)
    is_timed = Column(Boolean, default=False)
    
    # Relationships
    workout_day = relationship("WorkoutDay", back_populates="exercises")
    
    def __repr__(self):
        return f'<Exercise {self.name}>'

class WorkoutSession(Base):
    """Model for storing completed workout sessions."""
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workout_plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="workout_sessions")
    workout_plan = relationship("WorkoutPlan", back_populates="sessions")
    exercise_records = relationship("ExerciseRecord", back_populates="workout_session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<WorkoutSession {self.id} by User {self.user_id}>'

class ExerciseRecord(Base):
    """Model for storing exercise performance within a workout session."""
    __tablename__ = "exercise_records"

    id = Column(Integer, primary_key=True, index=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    exercise_name = Column(String(100), nullable=False)
    reps_completed = Column(Integer, nullable=False)
    duration = Column(Integer)  # Duration in seconds for timed exercises
    
    # Relationships
    workout_session = relationship("WorkoutSession", back_populates="exercise_records")
    feedback_records = relationship("FeedbackRecord", back_populates="exercise_record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ExerciseRecord {self.exercise_name} in Session {self.workout_session_id}>'

class FeedbackRecord(Base):
    """Model for storing feedback on exercise form."""
    __tablename__ = "feedback_records"

    id = Column(Integer, primary_key=True, index=True)
    exercise_record_id = Column(Integer, ForeignKey("exercise_records.id"), nullable=False)
    feedback_text = Column(String(255), nullable=False)
    frequency = Column(Integer, default=1)  # How many times this feedback was given
    severity = Column(String(20))  # LOW, MEDIUM, HIGH
    
    # Relationships
    exercise_record = relationship("ExerciseRecord", back_populates="feedback_records")
    
    def __repr__(self):
        return f'<FeedbackRecord "{self.feedback_text[:20]}..." for ExerciseRecord {self.exercise_record_id}>'