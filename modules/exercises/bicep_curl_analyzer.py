"""
Bicep curl exercise analyzer module.

This module provides functionality to analyze bicep curl form using pose landmarks.
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import mediapipe as mp

from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackPriority


class BicepCurlState(Enum):
    """States for the bicep curl exercise."""
    IDLE = 0
    CURL_START = 1
    CURL_UP = 2
    CURL_HOLD = 3
    CURL_DOWN = 4


class BicepCurlAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for bicep curl exercise form.
    
    Tracks arm angles, elbow movement, and body swing to provide 
    feedback on bicep curl form.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the bicep curl analyzer.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score.
        """
        super().__init__(thresholds, visibility_threshold)
        
        # Initialize bicep curl specific variables
        self.bicep_curl_state = BicepCurlState.IDLE
        self.prev_bicep_angle = 180
        
        # Thresholds specific to bicep curl
        self.curl_start_threshold = 160  # Arm is almost straight
        self.curl_up_threshold = 90      # Arm is bent halfway
        self.curl_down_threshold = 150   # Arm is mostly straight again
        
        # Tracking for form issues
        self.start_shoulder_pos = None
        self.start_hip_pos = None
        self.start_elbow_pos = None
        self.start_hip_shoulder_angle = None
        self.max_elbow_angle = 0
        self.max_swing_angle = 0
        
        # Smoothing
        self.elbow_angle_buffer = []
        
        # Confidence tracking
        self.elbow_detection_confidence = 1.0
        self.confidence_threshold = 0.7
        self.low_confidence_count = 0
        self.max_low_confidence_frames = 8
    
    def reset(self):
        """Reset the analyzer state."""
        super().reset()
        self.bicep_curl_state = BicepCurlState.IDLE
        self.prev_bicep_angle = 180
        self.start_shoulder_pos = None
        self.start_hip_pos = None
        self.start_elbow_pos = None
        self.start_hip_shoulder_angle = None
        self.max_elbow_angle = 0
        self.max_swing_angle = 0
        self.elbow_angle_buffer = []
        self.elbow_detection_confidence = 1.0
        self.low_confidence_count = 0
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], frame_time: float) -> Dict[str, Any]:
        """
        Process detected landmarks to analyze bicep curl form.
        
        Args:
            landmarks: Dictionary of detected landmarks from pose detector.
            frame_time: Time delta since last frame.
            
        Returns:
            Dictionary of analysis results.
        """
        mp_pose = mp.solutions.pose.PoseLandmark
        
        # Extract required landmarks
        left_shoulder = self.get_visible_point(landmarks, mp_pose.LEFT_SHOULDER.value)
        right_shoulder = self.get_visible_point(landmarks, mp_pose.RIGHT_SHOULDER.value)
        left_elbow = self.get_visible_point(landmarks, mp_pose.LEFT_ELBOW.value)
        right_elbow = self.get_visible_point(landmarks, mp_pose.RIGHT_ELBOW.value)
        left_wrist = self.get_visible_point(landmarks, mp_pose.LEFT_WRIST.value)
        right_wrist = self.get_visible_point(landmarks, mp_pose.RIGHT_WRIST.value)
        left_hip = self.get_visible_point(landmarks, mp_pose.LEFT_HIP.value)
        right_hip = self.get_visible_point(landmarks, mp_pose.RIGHT_HIP.value)
        
        # Check if we have enough visible landmarks
        left_arm_visible = all(p[2] >= self.visibility_threshold for p in [left_shoulder, left_elbow, left_wrist, left_hip])
        right_arm_visible = all(p[2] >= self.visibility_threshold for p in [right_shoulder, right_elbow, right_wrist, right_hip])
        
        if not (left_arm_visible or right_arm_visible):
            # Not enough landmarks visible for analysis
            self.feedback_manager.add_feedback(
                "Please position yourself so your arms are visible", 
                FeedbackPriority.HIGH
            )
            return self.get_analysis_result()
        
        # Determine which arm to analyze (use the one with better visibility or
        # the one performing the curl if both are visible)
        use_left_arm = False
        
        if left_arm_visible and right_arm_visible:
            # Calculate bicep angles for both arms
            left_bicep_angle = self.angle_calculator.angle_deg(left_shoulder, left_elbow, left_wrist)
            right_bicep_angle = self.angle_calculator.angle_deg(right_shoulder, right_elbow, right_wrist)
            
            # Use the arm with the smaller angle (more bent) if there's a significant difference
            if abs(left_bicep_angle - right_bicep_angle) > 20:
                use_left_arm = left_bicep_angle < right_bicep_angle
            else:
                # Default to better visibility if angles are similar
                left_visibility = min(left_shoulder[2], left_elbow[2], left_wrist[2], left_hip[2])
                right_visibility = min(right_shoulder[2], right_elbow[2], right_wrist[2], right_hip[2])
                use_left_arm = left_visibility > right_visibility
        else:
            # Use whichever arm is visible
            use_left_arm = left_arm_visible
        
        # Get the landmarks for the arm we're using
        shoulder = left_shoulder if use_left_arm else right_shoulder
        elbow = left_elbow if use_left_arm else right_elbow
        wrist = left_wrist if use_left_arm else right_wrist
        hip = left_hip if use_left_arm else right_hip
        
        # Calculate key angles
        bicep_angle = self.angle_calculator.angle_deg(shoulder, elbow, wrist)
        
        # Calculate elbow-torso angle to detect improper form
        elbow_torso_angle = None
        hip_shoulder_angle = None
        
        if use_left_arm:
            # Calculate left side angles
            if all(p[2] >= self.visibility_threshold for p in [left_hip, left_shoulder, left_elbow]):
                elbow_torso_angle = self.angle_calculator.angle_deg(left_hip, left_shoulder, left_elbow)
                hip_shoulder_angle = self.angle_calculator.calculate_hip_shoulder_angle(left_hip, left_shoulder)
        else:
            # Calculate right side angles
            if all(p[2] >= self.visibility_threshold for p in [right_hip, right_shoulder, right_elbow]):
                elbow_torso_angle = self.angle_calculator.angle_deg(right_hip, right_shoulder, right_elbow)
                hip_shoulder_angle = self.angle_calculator.calculate_hip_shoulder_angle(right_hip, right_shoulder)
        
        # Update angle history for smoothing
        self.update_angle_history("bicep_angle", bicep_angle)
        if elbow_torso_angle is not None:
            self.update_angle_history("elbow_torso_angle", elbow_torso_angle)
        
        # Process the bicep curl state
        self._process_bicep_curl_state(bicep_angle)
        
        # Analyze form for the current state
        is_start = self.bicep_curl_state == BicepCurlState.CURL_START and self.prev_bicep_angle > bicep_angle
        feedback = self._analyze_curl_form(
            shoulder, elbow, wrist, hip, 
            bicep_angle, elbow_torso_angle, hip_shoulder_angle, 
            is_start
        )
        
        # Update previous angle
        self.prev_bicep_angle = bicep_angle
        
        # Update the feedback manager frame counter
        self.feedback_manager.update_frame_counter()
        
        # Return result
        result = self.get_analysis_result()
        result.update({
            'exercise_state': self.bicep_curl_state.name,
            'bicep_angle': round(bicep_angle, 1),
            'elbow_movement': self.max_elbow_angle if self.max_elbow_angle else 0,
            'body_swing': self.max_swing_angle if self.max_swing_angle else 0,
            'arm_side': 'left' if use_left_arm else 'right'
        })
        
        return result
    
    def _process_bicep_curl_state(self, bicep_angle: float):
        """
        Process the bicep curl state based on the current angle.
        
        Args:
            bicep_angle: Current bicep angle in degrees.
        """
        if self.bicep_curl_state == BicepCurlState.IDLE:
            if bicep_angle < self.curl_start_threshold:
                self.bicep_curl_state = BicepCurlState.CURL_START
                self.feedback_manager.clear_feedback()
                self.form_issues_in_current_rep = False
                self.start_rep()
        
        elif self.bicep_curl_state == BicepCurlState.CURL_START:
            if bicep_angle < self.curl_up_threshold:
                self.bicep_curl_state = BicepCurlState.CURL_UP
            elif bicep_angle > self.prev_bicep_angle:
                self.bicep_curl_state = BicepCurlState.IDLE
                self.feedback_manager.add_feedback(
                    "Complete the curl motion", FeedbackPriority.MEDIUM
                )
        
        elif self.bicep_curl_state == BicepCurlState.CURL_UP:
            if bicep_angle <= self.prev_bicep_angle:
                self.bicep_curl_state = BicepCurlState.CURL_HOLD
        
        elif self.bicep_curl_state == BicepCurlState.CURL_HOLD:
            if bicep_angle > self.prev_bicep_angle:
                self.bicep_curl_state = BicepCurlState.CURL_DOWN
        
        elif self.bicep_curl_state == BicepCurlState.CURL_DOWN:
            if bicep_angle >= self.curl_down_threshold:
                self.bicep_curl_state = BicepCurlState.IDLE
                self.increment_rep_counter()
                
                # Add positive feedback if no form issues detected
                if not self.form_issues_in_current_rep:
                    self.feedback_manager.add_feedback(
                        "Good form! Keep it up", FeedbackPriority.LOW
                    )
    
    def _analyze_curl_form(self, shoulder, elbow, wrist, hip, 
                          bicep_angle, elbow_torso_angle, hip_shoulder_angle,
                          is_start):
        """
        Analyze bicep curl form and generate feedback.
        
        Args:
            shoulder, elbow, wrist, hip: Body landmarks.
            bicep_angle: Angle between shoulder, elbow, and wrist.
            elbow_torso_angle: Angle between hip, shoulder, and elbow.
            hip_shoulder_angle: Angle between hip and shoulder (for body swing).
            is_start: True if this is the start of a new rep.
            
        Returns:
            List of feedback strings.
        """
        if is_start or self.start_shoulder_pos is None:
            self.start_shoulder_pos = shoulder
            self.start_hip_pos = hip
            self.start_elbow_pos = elbow
            self.start_hip_shoulder_angle = hip_shoulder_angle
            return []
        
        has_issues = False
        
        # Check if the arm is extended fully at the bottom
        if bicep_angle > self.thresholds['bicep_curl_not_low_enough'] and self.bicep_curl_state in [
            BicepCurlState.CURL_START, BicepCurlState.IDLE
        ]:
            self.feedback_manager.add_feedback(
                "Extend your arm fully at the bottom", FeedbackPriority.MEDIUM
            )
            has_issues = True
        
        # Check if the curl goes high enough
        if bicep_angle > self.thresholds['bicep_curl_not_high_enough'] and self.bicep_curl_state == BicepCurlState.CURL_UP:
            self.feedback_manager.add_feedback(
                "Curl the weight higher to your shoulder", FeedbackPriority.MEDIUM
            )
            has_issues = True
        
        # Check for elbow movement (should stay fixed)
        elbow_movement = self.angle_calculator.find_distance(elbow[:2], self.start_elbow_pos[:2])
        if elbow_movement > self.thresholds['bicep_curl_elbow_movement']:
            self.feedback_manager.add_feedback(
                "Keep your elbow fixed in position", FeedbackPriority.HIGH
            )
            has_issues = True
        
        # Check for body swing
        if hip_shoulder_angle is not None and self.start_hip_shoulder_angle is not None:
            angle_diff = abs(hip_shoulder_angle - self.start_hip_shoulder_angle)
            self.max_swing_angle = max(self.max_swing_angle, angle_diff)
            
            if angle_diff > self.thresholds['bicep_curl_body_swing']:
                swing_severity = "slightly" if angle_diff <= 20 else "excessively"
                self.feedback_manager.add_feedback(
                    f"Your body is {swing_severity} swinging. Keep torso stable.", 
                    FeedbackPriority.HIGH if angle_diff > 20 else FeedbackPriority.MEDIUM
                )
                has_issues = True
        
        # Check for upper arm movement relative to torso
        if elbow_torso_angle is not None:
            # Smooth the elbow angle using a buffer
            self.elbow_angle_buffer.append(elbow_torso_angle)
            if len(self.elbow_angle_buffer) > 5:
                self.elbow_angle_buffer.pop(0)
            
            smoothed_elbow_angle = sum(self.elbow_angle_buffer) / len(self.elbow_angle_buffer)
            self.max_elbow_angle = max(self.max_elbow_angle, smoothed_elbow_angle)
            
            if self.max_elbow_angle > 35:
                self.feedback_manager.add_feedback(
                    "Keep your upper arm still against your body", FeedbackPriority.HIGH
                )
                has_issues = True
            
            self.low_confidence_count = 0
        else:
            # Track when we can't detect the angle properly
            self.low_confidence_count += 1
            if self.low_confidence_count >= self.max_low_confidence_frames:
                self.feedback_manager.add_feedback(
                    "Position yourself so your full arm is visible", FeedbackPriority.MEDIUM
                )
                self.low_confidence_count = 0
        
        # Update form issues flag
        if has_issues:
            self.form_issues_in_current_rep = True
        
        return self.feedback_manager.get_feedback()
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """Get the current analysis result."""
        result = super().get_analysis_result()
        result['exercise_state'] = self.bicep_curl_state.name
        return result