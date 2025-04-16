"""
Video processor module for exercise detection and analysis.

This module coordinates the pose detection and exercise analysis pipeline,
processing video frames to detect and analyze exercise form in real-time.
"""
import cv2
import numpy as np
import time
from typing import Dict, List, Any, Optional, Tuple, Type
import mediapipe as mp
from enum import Enum

from modules.pose_detector import PoseDetector
from modules.angle_calculator import AngleCalculator
from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackManager, FeedbackPriority

# Import exercise analyzers
from modules.exercises.bicep_curl_analyzer import BicepCurlAnalyzer
from modules.exercises.squat_analyzer import SquatAnalyzer
from modules.exercises.pushup_analyzer import PushupAnalyzer
from modules.exercises.lunge_analyzer import LungeAnalyzer
from modules.exercises.plank_analyzer import PlankAnalyzer
from modules.exercises.jumping_jack_analyzer import JumpingJackAnalyzer

from config import THRESHOLDS, VIDEO_WIDTH, VIDEO_HEIGHT


class ExerciseType(Enum):
    """Available exercise types for analysis."""
    BICEP_CURL = "bicep_curl"
    SQUAT = "squat"
    PUSHUP = "pushup"
    LUNGE = "lunge"
    PLANK = "plank"
    JUMPING_JACK = "jumping_jack"


class VideoProcessor:
    """
    Video processor for exercise detection and analysis.
    
    This class coordinates the pose detection pipeline and exercise analysis,
    processing video frames to detect and analyze exercise form in real-time.
    """
    
    def __init__(self, visibility_threshold: float = 0.6):
        """
        Initialize the video processor with detection and analysis components.
        
        Args:
            visibility_threshold: Minimum pose landmark visibility threshold.
        """
        # Initialize pose detection components
        self.pose_detector = PoseDetector()
        self.angle_calculator = AngleCalculator()
        self.visibility_threshold = visibility_threshold
        
        # Initialize exercise analyzers
        self.exercise_analyzers = {
            ExerciseType.BICEP_CURL: BicepCurlAnalyzer(THRESHOLDS, visibility_threshold),
            ExerciseType.SQUAT: SquatAnalyzer(THRESHOLDS, visibility_threshold),
            ExerciseType.PUSHUP: PushupAnalyzer(THRESHOLDS, visibility_threshold),
            ExerciseType.LUNGE: LungeAnalyzer(THRESHOLDS, visibility_threshold),
            ExerciseType.PLANK: PlankAnalyzer(THRESHOLDS, visibility_threshold),
            ExerciseType.JUMPING_JACK: JumpingJackAnalyzer(THRESHOLDS, visibility_threshold)
        }
        
        # Current active exercise
        self.current_exercise: Optional[ExerciseType] = None
        
        # Timer for frame processing
        self.last_frame_time = time.time()
        
        # Exercise session data
        self.exercise_data = {
            'current_exercise': None,
            'exercise_state': None,
            'rep_count': 0,
            'time_accumulated': 0,
            'feedback': [],
            'is_timed_exercise': False,
            'detailed_metrics': {},
        }
        
        # Session statistics
        self.session_stats = {
            'start_time': None,
            'exercise_durations': {},
            'rep_counts': {},
            'feedback_frequency': {},
            'exercise_sequence': []
        }
    
    def set_current_exercise(self, exercise_name: str, is_timed: bool = False) -> bool:
        """
        Set the current exercise for analysis.
        
        Args:
            exercise_name: Name of the exercise to set.
            is_timed: Whether this is a timed exercise or rep-based.
            
        Returns:
            bool: True if the exercise was set successfully, False otherwise.
        """
        try:
            # Convert string to enum
            exercise_type = ExerciseType(exercise_name.lower())
            
            # Reset the previous exercise analyzer if there was one
            if self.current_exercise:
                self.exercise_analyzers[self.current_exercise].reset()
            
            self.current_exercise = exercise_type
            
            # Configure the exercise analyzer
            self.exercise_analyzers[exercise_type].reset()
            self.exercise_analyzers[exercise_type].set_timed_exercise(is_timed)
            
            # Update exercise data
            self.exercise_data['current_exercise'] = exercise_name
            self.exercise_data['is_timed_exercise'] = is_timed
            self.exercise_data['rep_count'] = 0
            self.exercise_data['time_accumulated'] = 0
            self.exercise_data['feedback'] = []
            
            # Record in session stats if this is a new exercise
            current_time = time.time()
            if self.session_stats['start_time'] is None:
                self.session_stats['start_time'] = current_time
            
            self.session_stats['exercise_sequence'].append({
                'exercise': exercise_name,
                'start_time': current_time,
                'is_timed': is_timed
            })
            
            if exercise_name not in self.session_stats['rep_counts']:
                self.session_stats['rep_counts'][exercise_name] = 0
            
            if exercise_name not in self.session_stats['exercise_durations']:
                self.session_stats['exercise_durations'][exercise_name] = 0
            
            return True
        
        except (ValueError, KeyError):
            return False
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process a video frame to detect and analyze exercise form.
        
        Args:
            frame: Input video frame from camera or video source.
            
        Returns:
            Tuple of (processed frame with visualizations, exercise data dictionary).
        """
        # Resize frame if needed
        if frame.shape[1] != VIDEO_WIDTH or frame.shape[0] != VIDEO_HEIGHT:
            frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
        
        # Calculate frame time delta for timing exercises
        current_time = time.time()
        frame_time_delta = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        # Detect pose landmarks
        pose_results = self.pose_detector.find_pose(frame)
        
        # Extract and process landmarks if detected
        if pose_results.pose_landmarks:
            # Extract landmarks in a normalized format
            landmarks = self.pose_detector.extract_landmarks(pose_results, frame.shape)
            
            # Analyze the current exercise if one is set
            if self.current_exercise:
                # Get the appropriate analyzer
                analyzer = self.exercise_analyzers[self.current_exercise]
                
                # Analyze landmarks
                analysis_result = analyzer.analyze_landmarks(landmarks, frame_time_delta)
                
                # Update exercise data with analysis results
                self._update_exercise_data(analysis_result)
            
            # Draw pose landmarks on the frame
            frame = self.pose_detector.draw_landmarks(frame, pose_results)
            
            # Draw exercise-specific visualizations
            if self.current_exercise:
                frame = self._draw_exercise_visualizations(frame, landmarks)
        else:
            # No pose detected
            self.exercise_data['feedback'] = ["No pose detected. Please make sure your full body is visible."]
        
        # Draw basic information on the frame
        frame = self._draw_info_overlay(frame)
        
        return frame, self.exercise_data
    
    def _update_exercise_data(self, analysis_result: Dict[str, Any]):
        """
        Update exercise data with the latest analysis results.
        
        Args:
            analysis_result: Analysis results from the exercise analyzer.
        """
        # Update basic exercise data
        self.exercise_data['exercise_state'] = analysis_result.get('exercise_state', 'IDLE')
        self.exercise_data['rep_count'] = analysis_result.get('rep_count', 0)
        self.exercise_data['feedback'] = analysis_result.get('feedback', [])
        self.exercise_data['time_accumulated'] = analysis_result.get('time_accumulated', 0)
        
        # Update detailed metrics specific to this exercise
        detailed_metrics = {}
        for key, value in analysis_result.items():
            if key not in ['exercise_state', 'rep_count', 'feedback', 'time_accumulated']:
                detailed_metrics[key] = value
        
        self.exercise_data['detailed_metrics'] = detailed_metrics
        
        # Update session statistics
        if self.current_exercise:
            exercise_name = self.current_exercise.value
            
            # Update rep count
            self.session_stats['rep_counts'][exercise_name] = analysis_result.get('rep_count', 0)
            
            # Update exercise duration
            if analysis_result.get('is_timed_exercise', False):
                self.session_stats['exercise_durations'][exercise_name] = analysis_result.get('time_accumulated', 0)
            
            # Track feedback frequency
            for feedback in analysis_result.get('feedback', []):
                if feedback not in self.session_stats['feedback_frequency']:
                    self.session_stats['feedback_frequency'][feedback] = 0
                self.session_stats['feedback_frequency'][feedback] += 1
    
    def _draw_exercise_visualizations(self, frame: np.ndarray, landmarks: Dict[int, Dict[str, float]]) -> np.ndarray:
        """
        Draw exercise-specific visualizations on the frame.
        
        Args:
            frame: Input video frame.
            landmarks: Detected pose landmarks.
            
        Returns:
            Frame with exercise-specific visualizations.
        """
        # Draw different visualizations based on the current exercise
        if not self.current_exercise:
            return frame
        
        mp_pose = mp.solutions.pose.PoseLandmark
        h, w, _ = frame.shape
        
        # Draw angle annotations based on the exercise type
        if self.current_exercise == ExerciseType.BICEP_CURL:
            # Draw elbow angles for bicep curl
            for side in ['left', 'right']:
                if side == 'left':
                    shoulder = landmarks.get(mp_pose.LEFT_SHOULDER.value)
                    elbow = landmarks.get(mp_pose.LEFT_ELBOW.value)
                    wrist = landmarks.get(mp_pose.LEFT_WRIST.value)
                else:
                    shoulder = landmarks.get(mp_pose.RIGHT_SHOULDER.value)
                    elbow = landmarks.get(mp_pose.RIGHT_ELBOW.value)
                    wrist = landmarks.get(mp_pose.RIGHT_WRIST.value)
                
                if shoulder and elbow and wrist:
                    # Calculate angle
                    angle = self.angle_calculator.angle_deg(
                        [shoulder['x'], shoulder['y']], 
                        [elbow['x'], elbow['y']], 
                        [wrist['x'], wrist['y']]
                    )
                    
                    # Draw angle text
                    cv2.putText(
                        frame, f"{angle:.1f}°", 
                        (int(elbow['px']), int(elbow['py'])), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2
                    )
            
        elif self.current_exercise == ExerciseType.SQUAT:
            # Draw knee angles for squat
            for side in ['left', 'right']:
                if side == 'left':
                    hip = landmarks.get(mp_pose.LEFT_HIP.value)
                    knee = landmarks.get(mp_pose.LEFT_KNEE.value)
                    ankle = landmarks.get(mp_pose.LEFT_ANKLE.value)
                else:
                    hip = landmarks.get(mp_pose.RIGHT_HIP.value)
                    knee = landmarks.get(mp_pose.RIGHT_KNEE.value)
                    ankle = landmarks.get(mp_pose.RIGHT_ANKLE.value)
                
                if hip and knee and ankle:
                    # Calculate angle
                    angle = self.angle_calculator.angle_deg(
                        [hip['x'], hip['y']], 
                        [knee['x'], knee['y']], 
                        [ankle['x'], ankle['y']]
                    )
                    
                    # Draw angle text
                    cv2.putText(
                        frame, f"{angle:.1f}°", 
                        (int(knee['px']), int(knee['py'])), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2
                    )
            
            # Draw back angle
            left_hip = landmarks.get(mp_pose.LEFT_HIP.value)
            left_shoulder = landmarks.get(mp_pose.LEFT_SHOULDER.value)
            if left_hip and left_shoulder:
                back_angle = self.angle_calculator.calculate_vertical_angle(
                    [left_hip['x'], left_hip['y']], 
                    [left_shoulder['x'], left_shoulder['y']]
                )
                cv2.putText(
                    frame, f"Back: {back_angle:.1f}°", 
                    (10, h - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2
                )
        
        elif self.current_exercise == ExerciseType.PLANK:
            # Draw body alignment line for plank
            left_ankle = landmarks.get(mp_pose.LEFT_ANKLE.value)
            left_hip = landmarks.get(mp_pose.LEFT_HIP.value)
            left_shoulder = landmarks.get(mp_pose.LEFT_SHOULDER.value)
            
            if left_ankle and left_hip and left_shoulder:
                # Draw line from ankle to shoulder
                cv2.line(
                    frame,
                    (int(left_ankle['px']), int(left_ankle['py'])),
                    (int(left_shoulder['px']), int(left_shoulder['py'])),
                    (0, 255, 0), 2
                )
                
                # Draw hip position relative to line
                cv2.circle(
                    frame,
                    (int(left_hip['px']), int(left_hip['py'])),
                    5, (0, 0, 255), -1
                )
                
                # Get hip position metric
                hip_position = self.exercise_data['detailed_metrics'].get('hip_position', 0)
                
                cv2.putText(
                    frame, f"Hip: {hip_position:.2f}", 
                    (10, h - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2
                )
        
        return frame
    
    def _draw_info_overlay(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw information overlay on the frame.
        
        Args:
            frame: Input video frame.
            
        Returns:
            Frame with information overlay.
        """
        h, w, _ = frame.shape
        
        # Draw semi-transparent overlay for text background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 0), -1)
        cv2.rectangle(overlay, (0, h-90), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        
        # Draw exercise name and state
        current_exercise = self.exercise_data['current_exercise']
        if current_exercise:
            exercise_str = f"Exercise: {current_exercise.replace('_', ' ').title()}"
            cv2.putText(
                frame, exercise_str, 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
            
            # Draw exercise state
            state_str = f"State: {self.exercise_data['exercise_state']}"
            cv2.putText(
                frame, state_str, 
                (w - 200, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )
        else:
            cv2.putText(
                frame, "No exercise selected", 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
        
        # Draw rep count or time
        if self.exercise_data['is_timed_exercise']:
            time_str = f"Time: {self.exercise_data['time_accumulated']:.1f}s"
            cv2.putText(
                frame, time_str, 
                (10, h - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
        else:
            rep_str = f"Reps: {self.exercise_data['rep_count']}"
            cv2.putText(
                frame, rep_str, 
                (10, h - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
        
        # Draw feedback
        feedback = self.exercise_data.get('feedback', [])
        if feedback:
            feedback_str = f"Feedback: {feedback[0]}"
            cv2.putText(
                frame, feedback_str, 
                (10, h - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
            )
        
        return frame
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for the current exercise session.
        
        Returns:
            Dictionary containing session statistics.
        """
        stats = {
            'duration': time.time() - self.session_stats['start_time'] if self.session_stats['start_time'] else 0,
            'exercises': [],
            'common_feedback': []
        }
        
        # Process exercise data
        for exercise, rep_count in self.session_stats['rep_counts'].items():
            duration = self.session_stats['exercise_durations'].get(exercise, 0)
            
            # Get exercise-specific feedback
            exercise_feedback = {}
            for feedback, count in self.session_stats['feedback_frequency'].items():
                if exercise.lower() in feedback.lower():
                    exercise_feedback[feedback] = count
            
            stats['exercises'].append({
                'name': exercise,
                'rep_count': rep_count,
                'duration': duration,
                'feedback': sorted(
                    [{'text': fb, 'count': cnt} for fb, cnt in exercise_feedback.items()],
                    key=lambda x: x['count'],
                    reverse=True
                )
            })
        
        # Get most common feedback across all exercises
        stats['common_feedback'] = sorted(
            [{'text': fb, 'count': cnt} for fb, cnt in self.session_stats['feedback_frequency'].items()],
            key=lambda x: x['count'],
            reverse=True
        )[:5]  # Top 5 feedback items
        
        return stats
    
    def reset_session(self):
        """Reset the session statistics and exercise data."""
        if self.current_exercise:
            self.exercise_analyzers[self.current_exercise].reset()
        
        self.current_exercise = None
        
        self.exercise_data = {
            'current_exercise': None,
            'exercise_state': None,
            'rep_count': 0,
            'time_accumulated': 0,
            'feedback': [],
            'is_timed_exercise': False,
            'detailed_metrics': {},
        }
        
        self.session_stats = {
            'start_time': None,
            'exercise_durations': {},
            'rep_counts': {},
            'feedback_frequency': {},
            'exercise_sequence': []
        }