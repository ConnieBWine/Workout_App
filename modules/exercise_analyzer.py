"""
Base exercise analyzer module.

This module provides a base class for all exercise analyzers,
defining common functionality and interfaces.
"""
from enum import Enum
from typing import Dict, List, Tuple, Any, Optional
from modules.angle_calculator import AngleCalculator
from modules.feedback_manager import FeedbackManager, FeedbackPriority


class ExerciseState(Enum):
    """Base enum for exercise states."""
    IDLE = 0
    START = 1
    MIDDLE = 2
    END = 3


class ExerciseAnalyzer:
    """
    Base class for exercise analyzers.
    
    This class defines the common interfaces and functionality that all exercise
    analyzers should implement or inherit.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the exercise analyzer.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score.
        """
        self.thresholds = thresholds
        self.visibility_threshold = visibility_threshold
        self.angle_calculator = AngleCalculator()
        self.feedback_manager = FeedbackManager(window_size=10)
        
        # Exercise state tracking
        self.current_state = ExerciseState.IDLE
        self.rep_counter = 0
        self.last_angles = {}
        self.start_positions = {}
        self.max_angles = {}
        self.min_angles = {}
        
        # Rep detection flags
        self.rep_started = False
        self.form_issues_in_current_rep = False
        
        # Time tracking for timed exercises
        self.timer_active = False
        self.time_accumulated = 0  # seconds
        
        # History tracking
        self.angle_history = {}
        self.position_history = {}
        
        # For rep-based exercises
        self.is_timed_exercise = False
    
    def reset(self):
        """Reset the analyzer state."""
        self.current_state = ExerciseState.IDLE
        self.rep_started = False
        self.form_issues_in_current_rep = False
        self.feedback_manager.clear_feedback()
        self.start_positions = {}
        self.last_angles = {}
        self.max_angles = {}
        self.min_angles = {}
        self.angle_history = {}
        self.position_history = {}
        self.timer_active = False
        self.time_accumulated = 0
    
    def set_timed_exercise(self, is_timed: bool):
        """
        Set whether this is a timed exercise.
        
        Args:
            is_timed: True if this is a timed exercise, False for rep-based.
        """
        self.is_timed_exercise = is_timed
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], 
                          frame_time: float) -> Optional[Dict[str, Any]]:
        """
        Process detected landmarks to analyze exercise form.
        
        This is the main method called on each frame for exercise analysis.
        
        Args:
            landmarks: Dictionary of detected landmarks from pose detector.
            frame_time: Time delta since last frame.
            
        Returns:
            Dictionary of analysis results or None if landmarks are insufficient.
        """
        # Implement in derived classes
        raise NotImplementedError("Subclasses must implement analyze_landmarks")
    
    def check_visibility(self, landmarks: Dict[int, Dict[str, float]], 
                         landmark_indices: List[int]) -> bool:
        """
        Check if required landmarks are visible.
        
        Args:
            landmarks: Dictionary of landmarks.
            landmark_indices: List of required landmark indices.
            
        Returns:
            True if all landmarks are visible above threshold.
        """
        for idx in landmark_indices:
            if idx not in landmarks or landmarks[idx]['visibility'] < self.visibility_threshold:
                return False
        return True
    
    def update_angle_history(self, angle_name: str, angle_value: float, 
                            max_history: int = 10):
        """
        Update angle history for tracking and smoothing.
        
        Args:
            angle_name: Name of the angle to track.
            angle_value: Current angle value.
            max_history: Maximum number of values to keep.
        """
        if angle_name not in self.angle_history:
            self.angle_history[angle_name] = []
        
        self.angle_history[angle_name].append(angle_value)
        
        # Keep history limited
        if len(self.angle_history[angle_name]) > max_history:
            self.angle_history[angle_name].pop(0)
    
    def get_smoothed_angle(self, angle_name: str, default: float = 0) -> float:
        """
        Get a smoothed angle value from history.
        
        Args:
            angle_name: Name of the angle to get.
            default: Default value if no history exists.
            
        Returns:
            Averaged angle value.
        """
        if angle_name not in self.angle_history or not self.angle_history[angle_name]:
            return default
        
        return sum(self.angle_history[angle_name]) / len(self.angle_history[angle_name])
    
    def provide_feedback(self) -> List[str]:
        """
        Get the current feedback to display to the user.
        
        Returns:
            List of feedback strings ordered by priority.
        """
        return self.feedback_manager.get_feedback()
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """
        Get the current analysis result.
        
        Returns:
            Dictionary with exercise state and metrics.
        """
        return {
            'exercise_state': self.current_state.name,
            'rep_count': self.rep_counter,
            'feedback': self.provide_feedback(),
            'timed_exercise': self.is_timed_exercise,
            'time_accumulated': self.time_accumulated if self.is_timed_exercise else None
        }
    
    def increment_rep_counter(self):
        """Increment the repetition counter."""
        self.rep_counter += 1
        self.rep_started = False
        self.form_issues_in_current_rep = False
    
    def start_rep(self):
        """Mark the start of a new repetition."""
        self.rep_started = True
        self.form_issues_in_current_rep = False
    
    def check_rep_completion(self, completion_condition: bool) -> bool:
        """
        Check if a repetition has been completed.
        
        Args:
            completion_condition: Condition that must be true for rep completion.
            
        Returns:
            True if the rep is complete.
        """
        if self.rep_started and completion_condition:
            self.increment_rep_counter()
            return True
        return False
    
    def reset_counter(self):
        """Reset the repetition counter."""
        self.rep_counter = 0

    def is_landmark_visible(self, landmarks: Dict[int, Dict[str, float]], 
                          landmark_idx: int) -> bool:
        """
        Check if a specific landmark is visible.
        
        Args:
            landmarks: Dictionary of landmarks.
            landmark_idx: Index of the landmark to check.
            
        Returns:
            True if the landmark is visible above threshold.
        """
        return (landmark_idx in landmarks and 
                landmarks[landmark_idx]['visibility'] >= self.visibility_threshold)
    
    def get_visible_point(self, landmarks: Dict[int, Dict[str, float]], 
                        landmark_idx: int, default: List[float] = None) -> List[float]:
        """
        Get a landmark point if visible, otherwise return default.
        
        Args:
            landmarks: Dictionary of landmarks.
            landmark_idx: Index of the landmark to get.
            default: Default point to return if landmark not visible.
            
        Returns:
            Point coordinates [x, y, visibility] or default.
        """
        if self.is_landmark_visible(landmarks, landmark_idx):
            lm = landmarks[landmark_idx]
            return [lm['x'], lm['y'], lm['visibility']]
        return default or [0, 0, 0]
    
    def update_time(self, frame_time: float):
        """
        Update accumulated time for timed exercises.
        
        Args:
            frame_time: Time delta since last frame in seconds.
        """
        if self.timer_active and self.is_timed_exercise:
            self.time_accumulated += frame_time