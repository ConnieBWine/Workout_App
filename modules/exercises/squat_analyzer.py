"""
Squat exercise analyzer module.

This module provides functionality to analyze squat form using pose landmarks.
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import mediapipe as mp

from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackPriority


class SquatState(Enum):
    """States for the squat exercise."""
    IDLE = 0
    SQUAT_START = 1
    SQUAT_DOWN = 2
    SQUAT_HOLD = 3
    SQUAT_UP = 4


class SquatAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for squat exercise form.
    
    Tracks knee angles, back angle, and hip position to provide 
    feedback on squat form.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the squat analyzer.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score.
        """
        super().__init__(thresholds, visibility_threshold)
        
        # Initialize squat specific variables
        self.squat_state = SquatState.IDLE
        self.prev_knee_angle = 180
        
        # Thresholds specific to squat
        self.start_threshold = 160    # Knees are almost straight
        self.squat_threshold = 100    # Knees are bent for a proper squat
        
        # Tracking for form issues
        self.start_hip_height = None
        self.lowest_hip_height = None
        self.start_knee_position = None
        self.start_ankle_position = None
        self.max_back_angle = 0
        self.min_back_angle = 90
        self.min_knee_angle = 180
        
        # Knee tracking
        self.knee_tracking_issues = 0
        self.max_knee_tracking_issues = 5
    
    def reset(self):
        """Reset the analyzer state."""
        super().reset()
        self.squat_state = SquatState.IDLE
        self.prev_knee_angle = 180
        self.start_hip_height = None
        self.lowest_hip_height = None
        self.start_knee_position = None
        self.start_ankle_position = None
        self.max_back_angle = 0
        self.min_back_angle = 90
        self.min_knee_angle = 180
        self.knee_tracking_issues = 0
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], frame_time: float) -> Dict[str, Any]:
        """
        Process detected landmarks to analyze squat form.
        
        Args:
            landmarks: Dictionary of detected landmarks from pose detector.
            frame_time: Time delta since last frame.
            
        Returns:
            Dictionary of analysis results.
        """
        mp_pose = mp.solutions.pose.PoseLandmark
        
        # Extract required landmarks
        left_hip = self.get_visible_point(landmarks, mp_pose.LEFT_HIP.value)
        right_hip = self.get_visible_point(landmarks, mp_pose.RIGHT_HIP.value)
        left_knee = self.get_visible_point(landmarks, mp_pose.LEFT_KNEE.value)
        right_knee = self.get_visible_point(landmarks, mp_pose.RIGHT_KNEE.value)
        left_ankle = self.get_visible_point(landmarks, mp_pose.LEFT_ANKLE.value)
        right_ankle = self.get_visible_point(landmarks, mp_pose.RIGHT_ANKLE.value)
        left_shoulder = self.get_visible_point(landmarks, mp_pose.LEFT_SHOULDER.value)
        right_shoulder = self.get_visible_point(landmarks, mp_pose.RIGHT_SHOULDER.value)
        
        # Check if we have enough visible landmarks
        lower_body_visible = all(
            p[2] >= self.visibility_threshold for p in 
            [left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]
        )
        
        if not lower_body_visible:
            # Not enough landmarks visible for analysis
            self.feedback_manager.add_feedback(
                "Please position yourself so your lower body is visible", 
                FeedbackPriority.HIGH
            )
            return self.get_analysis_result()
        
        # Calculate key angles
        left_knee_angle = self.angle_calculator.angle_deg(left_hip, left_knee, left_ankle)
        right_knee_angle = self.angle_calculator.angle_deg(right_hip, right_knee, right_ankle)
        knee_angle = (left_knee_angle + right_knee_angle) / 2
        
        # Calculate back angle (angle between hips and shoulders relative to vertical)
        back_angle_left = self.angle_calculator.angle_deg(
            left_hip, left_shoulder, 
            [left_shoulder[0], left_hip[1]]  # Vertical point above hip
        )
        back_angle_right = self.angle_calculator.angle_deg(
            right_hip, right_shoulder, 
            [right_shoulder[0], right_hip[1]]  # Vertical point above hip
        )
        back_angle = (back_angle_left + back_angle_right) / 2
        
        # Calculate knee tracking (knees should track over toes)
        left_knee_tracking = self._check_knee_tracking(left_knee, left_ankle, left_hip)
        right_knee_tracking = self._check_knee_tracking(right_knee, right_ankle, right_hip)
        
        # Update angle history for smoothing
        self.update_angle_history("knee_angle", knee_angle)
        self.update_angle_history("back_angle", back_angle)
        
        # Process the squat state
        self._process_squat_state(knee_angle)
        
        # Analyze form for the current state
        feedback = self._analyze_squat_form(
            knee_angle, back_angle, left_knee_tracking, right_knee_tracking
        )
        
        # Update previous angle
        self.prev_knee_angle = knee_angle
        
        # Track hip height for depth analysis
        hip_height = (left_hip[1] + right_hip[1]) / 2
        if self.start_hip_height is None or self.squat_state == SquatState.IDLE:
            self.start_hip_height = hip_height
        
        if self.lowest_hip_height is None or hip_height > self.lowest_hip_height:
            self.lowest_hip_height = hip_height
        
        # Update form tracking variables
        self.min_knee_angle = min(self.min_knee_angle, knee_angle)
        self.max_back_angle = max(self.max_back_angle, back_angle)
        self.min_back_angle = min(self.min_back_angle, back_angle)
        
        # Update the feedback manager frame counter
        self.feedback_manager.update_frame_counter()
        
        # Return result
        result = self.get_analysis_result()
        result.update({
            'exercise_state': self.squat_state.name,
            'knee_angle': round(knee_angle, 1),
            'back_angle': round(back_angle, 1),
            'depth_percent': self._calculate_depth_percentage(hip_height),
        })
        
        return result
    
    def _process_squat_state(self, knee_angle: float):
        """
        Process the squat state based on the current angle.
        
        Args:
            knee_angle: Current average knee angle in degrees.
        """
        if self.squat_state == SquatState.IDLE:
            if knee_angle < self.start_threshold:
                self.squat_state = SquatState.SQUAT_START
                self.feedback_manager.clear_feedback()
                self.form_issues_in_current_rep = False
                self.start_rep()
        
        elif self.squat_state == SquatState.SQUAT_START:
            if knee_angle < self.squat_threshold:
                self.squat_state = SquatState.SQUAT_DOWN
            elif knee_angle > self.prev_knee_angle:
                # Going back up without completing the squat
                self.squat_state = SquatState.IDLE
                self.feedback_manager.add_feedback(
                    "Lower yourself into a proper squat", FeedbackPriority.MEDIUM
                )
        
        elif self.squat_state == SquatState.SQUAT_DOWN:
            if knee_angle <= self.prev_knee_angle:
                self.squat_state = SquatState.SQUAT_HOLD
            
        elif self.squat_state == SquatState.SQUAT_HOLD:
            if knee_angle > self.prev_knee_angle:
                self.squat_state = SquatState.SQUAT_UP
                # Analyze the deepest point of the squat
                self._analyze_squat_depth()
        
        elif self.squat_state == SquatState.SQUAT_UP:
            if knee_angle >= self.start_threshold:
                self.squat_state = SquatState.IDLE
                self.increment_rep_counter()
                
                # Add positive feedback if no form issues detected
                if not self.form_issues_in_current_rep:
                    self.feedback_manager.add_feedback(
                        "Good form! Keep it up", FeedbackPriority.LOW
                    )
    
    def _analyze_squat_form(self, knee_angle, back_angle, left_knee_tracking, right_knee_tracking):
        """
        Analyze squat form and generate feedback.
        
        Args:
            knee_angle: Average angle of both knees.
            back_angle: Angle of the back relative to vertical.
            left_knee_tracking, right_knee_tracking: Knee tracking indicators.
            
        Returns:
            List of feedback strings.
        """
        has_issues = False
        
        # Only analyze form when in an active squat state
        if self.squat_state not in [SquatState.SQUAT_DOWN, SquatState.SQUAT_HOLD, SquatState.SQUAT_UP]:
            return []
        
        # Check back angle (forward lean)
        if back_angle < self.thresholds['squat_forward_bend_too_little']:
            self.feedback_manager.add_feedback(
                "Lean forward slightly to maintain balance", FeedbackPriority.MEDIUM
            )
            has_issues = True
        elif back_angle > self.thresholds['squat_forward_bend_too_much']:
            self.feedback_manager.add_feedback(
                "Keep your back more upright", FeedbackPriority.HIGH
            )
            has_issues = True
        
        # Check squat depth
        if self.squat_state == SquatState.SQUAT_HOLD:
            if knee_angle < self.thresholds['squat_too_deep']:
                self.feedback_manager.add_feedback(
                    "You're squatting too deep, raise slightly", FeedbackPriority.MEDIUM
                )
                has_issues = True
            elif knee_angle > self.thresholds['squat_not_deep_enough']:
                self.feedback_manager.add_feedback(
                    "Lower your hips more for a proper squat", FeedbackPriority.HIGH
                )
                has_issues = True
        
        # Check knee tracking
        if not left_knee_tracking or not right_knee_tracking:
            self.knee_tracking_issues += 1
            
            if self.knee_tracking_issues >= self.max_knee_tracking_issues:
                if not left_knee_tracking and not right_knee_tracking:
                    self.feedback_manager.add_feedback(
                        "Keep your knees in line with your toes", FeedbackPriority.HIGH
                    )
                elif not left_knee_tracking:
                    self.feedback_manager.add_feedback(
                        "Keep your left knee in line with your toes", FeedbackPriority.MEDIUM
                    )
                else:
                    self.feedback_manager.add_feedback(
                        "Keep your right knee in line with your toes", FeedbackPriority.MEDIUM
                    )
                
                self.knee_tracking_issues = 0
                has_issues = True
        else:
            self.knee_tracking_issues = 0
        
        # Update form issues flag
        if has_issues:
            self.form_issues_in_current_rep = True
        
        return self.feedback_manager.get_feedback()
    
    def _analyze_squat_depth(self):
        """Analyze the depth of the squat at its lowest point."""
        if self.min_knee_angle < self.thresholds['squat_too_deep']:
            self.feedback_manager.add_feedback(
                "Try not to squat quite as deep", FeedbackPriority.LOW
            )
        elif self.min_knee_angle > self.thresholds['squat_not_deep_enough']:
            self.feedback_manager.add_feedback(
                "Try to squat deeper, lowering your hips more", FeedbackPriority.MEDIUM
            )
    
    def _check_knee_tracking(self, knee, ankle, hip):
        """
        Check if the knee is tracking properly over the foot.
        
        Args:
            knee: Knee landmark coordinates.
            ankle: Ankle landmark coordinates.
            hip: Hip landmark coordinates.
            
        Returns:
            bool: True if knee is tracking properly.
        """
        # Project the knee onto the ankle-hip line
        ankle_to_hip = np.array([hip[0] - ankle[0], hip[1] - ankle[1]])
        ankle_to_knee = np.array([knee[0] - ankle[0], knee[1] - ankle[1]])
        
        # Normalize ankle_to_hip
        ankle_to_hip_length = np.linalg.norm(ankle_to_hip)
        if ankle_to_hip_length == 0:
            return True  # Can't determine tracking if ankle and hip are at same position
            
        ankle_to_hip_normalized = ankle_to_hip / ankle_to_hip_length
        
        # Project ankle_to_knee onto ankle_to_hip
        projection_length = np.dot(ankle_to_knee, ankle_to_hip_normalized)
        projection = projection_length * ankle_to_hip_normalized
        
        # Calculate perpendicular distance
        perpendicular = ankle_to_knee - projection
        perpendicular_distance = np.linalg.norm(perpendicular)
        
        # Check if knee is tracking properly (within 15% of leg length)
        acceptable_distance = ankle_to_hip_length * 0.15
        return perpendicular_distance <= acceptable_distance
    
    def _calculate_depth_percentage(self, current_hip_height):
        """
        Calculate the percentage of squat depth.
        
        Args:
            current_hip_height: Current y-coordinate of hip.
            
        Returns:
            float: Percentage of max depth (0-100).
        """
        if self.start_hip_height is None or self.lowest_hip_height is None:
            return 0
        
        if self.start_hip_height == self.lowest_hip_height:
            return 0
            
        # Calculate as percentage of maximum possible depth
        depth_percent = ((current_hip_height - self.start_hip_height) / 
                        (self.lowest_hip_height - self.start_hip_height)) * 100
        
        return round(max(0, min(100, depth_percent)), 1)
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """Get the current analysis result."""
        result = super().get_analysis_result()
        result['exercise_state'] = self.squat_state.name
        return result