"""
Lunge exercise analyzer module.

This module provides comprehensive analysis of lunge exercise form using pose landmarks,
detecting common form issues and providing real-time feedback.
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import mediapipe as mp

from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackPriority


class LungeState(Enum):
    """Discrete states for tracking lunge exercise progression."""
    IDLE = 0
    LUNGE_START = 1
    LUNGE_DOWN = 2
    LUNGE_HOLD = 3
    LUNGE_UP = 4


class LungeAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for lunge exercise form.
    
    Tracks knee angles, torso angle, and overall balance to provide
    detailed feedback on lunge form and technique.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the lunge analyzer with form thresholds and visibility requirements.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score to consider points valid.
        """
        super().__init__(thresholds, visibility_threshold)
        
        # Initialize lunge-specific state variables
        self.lunge_state = LungeState.IDLE
        self.prev_front_knee_angle = 180
        self.prev_back_knee_angle = 180
        
        # Thresholds specific to lunge form
        self.start_threshold = 160    # Knees are almost straight
        self.lunge_front_threshold = 100  # Front knee bend threshold
        self.lunge_back_threshold = 120   # Back knee bend threshold
        
        # Form tracking variables
        self.min_front_knee_angle = 180
        self.min_back_knee_angle = 180
        self.max_torso_angle = 0
        self.min_torso_angle = 90
        
        # Balance and alignment tracking
        self.balance_issues = 0
        self.max_balance_issues = 5
        self.front_leg_tracking_issues = 0
        self.back_leg_position_issues = 0
        
        # Current active leg (left or right as front leg)
        self.active_leg = None  # 'left' or 'right'
        
        # Track stance stability
        self.stance_width = None
        self.stance_stability = 1.0
    
    def reset(self):
        """Reset the analyzer state for a new exercise sequence."""
        super().reset()
        self.lunge_state = LungeState.IDLE
        self.prev_front_knee_angle = 180
        self.prev_back_knee_angle = 180
        self.min_front_knee_angle = 180
        self.min_back_knee_angle = 180
        self.max_torso_angle = 0
        self.min_torso_angle = 90
        self.balance_issues = 0
        self.front_leg_tracking_issues = 0
        self.back_leg_position_issues = 0
        self.active_leg = None
        self.stance_width = None
        self.stance_stability = 1.0
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], frame_time: float) -> Dict[str, Any]:
        """
        Process detected landmarks to analyze lunge form in detail.
        
        Args:
            landmarks: Dictionary of detected landmarks from pose detector.
            frame_time: Time delta since last frame.
            
        Returns:
            Dictionary of comprehensive analysis results including angles and feedback.
        """
        mp_pose = mp.solutions.pose.PoseLandmark
        
        # Extract required landmarks for lunge analysis
        left_hip = self.get_visible_point(landmarks, mp_pose.LEFT_HIP.value)
        right_hip = self.get_visible_point(landmarks, mp_pose.RIGHT_HIP.value)
        left_knee = self.get_visible_point(landmarks, mp_pose.LEFT_KNEE.value)
        right_knee = self.get_visible_point(landmarks, mp_pose.RIGHT_KNEE.value)
        left_ankle = self.get_visible_point(landmarks, mp_pose.LEFT_ANKLE.value)
        right_ankle = self.get_visible_point(landmarks, mp_pose.RIGHT_ANKLE.value)
        left_shoulder = self.get_visible_point(landmarks, mp_pose.LEFT_SHOULDER.value)
        right_shoulder = self.get_visible_point(landmarks, mp_pose.RIGHT_SHOULDER.value)
        
        # Check if we have enough visible landmarks for proper analysis
        lower_body_visible = all(
            p[2] >= self.visibility_threshold for p in 
            [left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]
        )
        
        if not lower_body_visible:
            # Not enough landmarks visible for analysis
            self.feedback_manager.add_feedback(
                "Please position yourself so your full lower body is visible", 
                FeedbackPriority.HIGH
            )
            return self.get_analysis_result()
        
        # Calculate knee angles for both legs
        left_knee_angle = self.angle_calculator.angle_deg(left_hip, left_knee, left_ankle)
        right_knee_angle = self.angle_calculator.angle_deg(right_hip, right_knee, right_ankle)
        
        # Determine which leg is front (more bent) if not already established
        if self.active_leg is None or self.lunge_state == LungeState.IDLE:
            # Use the leg with more bend as the front leg
            if left_knee_angle < right_knee_angle:
                self.active_leg = 'left'
            else:
                self.active_leg = 'right'
        
        # Assign front and back leg angles based on active leg
        if self.active_leg == 'left':
            front_knee_angle = left_knee_angle
            back_knee_angle = right_knee_angle
            front_hip = left_hip
            front_knee = left_knee
            front_ankle = left_ankle
            back_hip = right_hip
            back_knee = right_knee
            back_ankle = right_ankle
        else:
            front_knee_angle = right_knee_angle
            back_knee_angle = left_knee_angle
            front_hip = right_hip
            front_knee = right_knee
            front_ankle = right_ankle
            back_hip = left_hip
            back_knee = left_knee
            back_ankle = left_ankle
        
        # Calculate torso angle (should be upright)
        left_torso_angle = self.angle_calculator.calculate_vertical_angle(left_hip[:2], left_shoulder[:2])
        right_torso_angle = self.angle_calculator.calculate_vertical_angle(right_hip[:2], right_shoulder[:2])
        torso_angle = (left_torso_angle + right_torso_angle) / 2
        
        # Calculate stance width and stability
        stance_width = self.angle_calculator.find_distance(left_ankle[:2], right_ankle[:2])
        if self.stance_width is None:
            self.stance_width = stance_width
        
        # Normalized stance stability (1.0 is stable, lower is less stable)
        stance_stability = min(1.0, self.stance_width / max(stance_width, 0.01))
        self.stance_stability = 0.8 * self.stance_stability + 0.2 * stance_stability  # Smooth
        
        # Check front knee tracking (should track over ankle, not inward or outward)
        knee_tracking = self._check_knee_tracking(front_hip, front_knee, front_ankle)
        
        # Check back leg position (should be properly positioned)
        back_leg_position = self._check_back_leg_position(back_hip, back_knee, back_ankle)
        
        # Update angle history for smoothing
        self.update_angle_history("front_knee_angle", front_knee_angle)
        self.update_angle_history("back_knee_angle", back_knee_angle)
        self.update_angle_history("torso_angle", torso_angle)
        
        # Process the lunge state based on knee angles
        self._process_lunge_state(front_knee_angle, back_knee_angle)
        
        # Analyze form for the current state
        feedback = self._analyze_lunge_form(
            front_knee_angle, back_knee_angle, torso_angle, 
            knee_tracking, back_leg_position
        )
        
        # Update previous angles
        self.prev_front_knee_angle = front_knee_angle
        self.prev_back_knee_angle = back_knee_angle
        
        # Update form tracking variables
        self.min_front_knee_angle = min(self.min_front_knee_angle, front_knee_angle)
        self.min_back_knee_angle = min(self.min_back_knee_angle, back_knee_angle)
        self.max_torso_angle = max(self.max_torso_angle, torso_angle)
        self.min_torso_angle = min(self.min_torso_angle, torso_angle)
        
        # Update the feedback manager frame counter
        self.feedback_manager.update_frame_counter()
        
        # Return comprehensive analysis result
        result = self.get_analysis_result()
        result.update({
            'exercise_state': self.lunge_state.name,
            'front_knee_angle': round(front_knee_angle, 1),
            'back_knee_angle': round(back_knee_angle, 1),
            'torso_angle': round(torso_angle, 1),
            'active_leg': self.active_leg,
            'stance_stability': round(self.stance_stability, 2),
            'knee_tracking': knee_tracking,
            'back_leg_position': back_leg_position
        })
        
        return result
    
    def _process_lunge_state(self, front_knee_angle: float, back_knee_angle: float):
        """
        Process the lunge state based on current knee angles and previous state.
        
        Args:
            front_knee_angle: Angle of the front knee.
            back_knee_angle: Angle of the back knee.
        """
        if self.lunge_state == LungeState.IDLE:
            if front_knee_angle < self.start_threshold:
                self.lunge_state = LungeState.LUNGE_START
                self.feedback_manager.clear_feedback()
                self.form_issues_in_current_rep = False
                self.start_rep()
        
        elif self.lunge_state == LungeState.LUNGE_START:
            if front_knee_angle < self.lunge_front_threshold and back_knee_angle < self.lunge_back_threshold:
                self.lunge_state = LungeState.LUNGE_DOWN
            elif front_knee_angle > self.prev_front_knee_angle and back_knee_angle > self.prev_back_knee_angle:
                # Going back up without completing the lunge
                self.lunge_state = LungeState.IDLE
                self.feedback_manager.add_feedback(
                    "Complete the lunge movement by lowering your body", FeedbackPriority.MEDIUM
                )
        
        elif self.lunge_state == LungeState.LUNGE_DOWN:
            if front_knee_angle <= self.prev_front_knee_angle and back_knee_angle <= self.prev_back_knee_angle:
                self.lunge_state = LungeState.LUNGE_HOLD
            
        elif self.lunge_state == LungeState.LUNGE_HOLD:
            if front_knee_angle > self.prev_front_knee_angle or back_knee_angle > self.prev_back_knee_angle:
                self.lunge_state = LungeState.LUNGE_UP
                # Analyze the lowest point of the lunge
                self._analyze_lunge_depth()
        
        elif self.lunge_state == LungeState.LUNGE_UP:
            if front_knee_angle >= self.start_threshold and back_knee_angle >= self.start_threshold:
                self.lunge_state = LungeState.IDLE
                self.increment_rep_counter()
                
                # Add positive feedback if no form issues detected
                if not self.form_issues_in_current_rep:
                    self.feedback_manager.add_feedback(
                        "Excellent lunge form!", FeedbackPriority.LOW
                    )
    
    def _analyze_lunge_form(self, front_knee_angle, back_knee_angle, torso_angle, 
                          knee_tracking, back_leg_position):
        """
        Analyze lunge form against established criteria and generate targeted feedback.
        
        Args:
            front_knee_angle: Angle of the front knee.
            back_knee_angle: Angle of the back knee.
            torso_angle: Angle of the torso relative to vertical.
            knee_tracking: Boolean indicating if front knee is tracking properly.
            back_leg_position: Boolean indicating if back leg is positioned properly.
            
        Returns:
            List of feedback strings ordered by priority.
        """
        has_issues = False
        
        # Only analyze form when in an active lunge state
        if self.lunge_state not in [LungeState.LUNGE_DOWN, LungeState.LUNGE_HOLD, LungeState.LUNGE_UP]:
            return []
        
        # Check front knee angle (should bend to ~90 degrees)
        if self.lunge_state == LungeState.LUNGE_HOLD:
            if front_knee_angle > self.thresholds['lunge_knee_angle_front']:
                self.feedback_manager.add_feedback(
                    "Bend your front knee more (aim for 90 degrees)", FeedbackPriority.HIGH
                )
                has_issues = True
            elif front_knee_angle < 75:  # Too much bend can strain the knee
                self.feedback_manager.add_feedback(
                    "Don't bend your front knee too much", FeedbackPriority.MEDIUM
                )
                has_issues = True
        
        # Check back knee angle (should bend but not touch ground)
        if self.lunge_state == LungeState.LUNGE_HOLD:
            if back_knee_angle > self.thresholds['lunge_knee_angle_back']:
                self.feedback_manager.add_feedback(
                    "Lower your back knee more", FeedbackPriority.MEDIUM
                )
                has_issues = True
            elif back_knee_angle < 80:  # Too low might touch ground
                self.feedback_manager.add_feedback(
                    "Keep your back knee slightly off the ground", FeedbackPriority.LOW
                )
                has_issues = True
        
        # Check torso position (should be upright)
        if abs(torso_angle) > self.thresholds['lunge_torso_angle']:
            if torso_angle > 0:  # Leaning forward
                self.feedback_manager.add_feedback(
                    "Keep your torso more upright, don't lean forward", FeedbackPriority.HIGH
                )
            else:  # Leaning backward
                self.feedback_manager.add_feedback(
                    "Keep your torso upright, don't lean back", FeedbackPriority.HIGH
                )
            has_issues = True
        
        # Check front knee tracking (should be over ankle, not inside or outside)
        if not knee_tracking:
            self.front_leg_tracking_issues += 1
            
            if self.front_leg_tracking_issues >= self.max_balance_issues:
                self.feedback_manager.add_feedback(
                    f"Keep your {self.active_leg} knee aligned over your ankle", 
                    FeedbackPriority.HIGH
                )
                self.front_leg_tracking_issues = 0
                has_issues = True
        else:
            self.front_leg_tracking_issues = 0
        
        # Check back leg position
        if not back_leg_position:
            self.back_leg_position_issues += 1
            
            if self.back_leg_position_issues >= self.max_balance_issues:
                self.feedback_manager.add_feedback(
                    "Position your back leg properly with knee pointing down", 
                    FeedbackPriority.MEDIUM
                )
                self.back_leg_position_issues = 0
                has_issues = True
        else:
            self.back_leg_position_issues = 0
        
        # Check stance stability
        if self.stance_stability < 0.7:  # Arbitrary threshold
            self.balance_issues += 1
            
            if self.balance_issues >= self.max_balance_issues:
                self.feedback_manager.add_feedback(
                    "Maintain a stable stance throughout the lunge", 
                    FeedbackPriority.MEDIUM
                )
                self.balance_issues = 0
                has_issues = True
        else:
            self.balance_issues = 0
        
        # Update form issues flag
        if has_issues:
            self.form_issues_in_current_rep = True
        
        return self.feedback_manager.get_feedback()
    
    def _analyze_lunge_depth(self):
        """Analyze the depth of the lunge at its lowest point for comprehensive feedback."""
        # Check front knee depth
        if self.min_front_knee_angle > self.thresholds['lunge_knee_angle_front']:
            self.feedback_manager.add_feedback(
                "Try to bend your front knee more in your lunges", FeedbackPriority.MEDIUM
            )
        
        # Check back knee position
        if self.min_back_knee_angle > self.thresholds['lunge_knee_angle_back']:
            self.feedback_manager.add_feedback(
                "Lower your back knee more in your lunges", FeedbackPriority.LOW
            )
    
    def _check_knee_tracking(self, hip, knee, ankle):
        """
        Check if the front knee is tracking properly over the ankle.
        
        Args:
            hip: Hip landmark coordinates.
            knee: Knee landmark coordinates.
            ankle: Ankle landmark coordinates.
            
        Returns:
            bool: True if knee is tracking properly.
        """
        # Project the knee onto the ankle-hip line
        hip_to_ankle = np.array([ankle[0] - hip[0], ankle[1] - hip[1]])
        hip_to_knee = np.array([knee[0] - hip[0], knee[1] - hip[1]])
        
        # Normalize vectors
        hip_to_ankle_length = np.linalg.norm(hip_to_ankle)
        if hip_to_ankle_length == 0:
            return True  # Avoid division by zero
            
        hip_to_ankle_normalized = hip_to_ankle / hip_to_ankle_length
        
        # Project hip_to_knee onto hip_to_ankle
        projection_length = np.dot(hip_to_knee, hip_to_ankle_normalized)
        projection = projection_length * hip_to_ankle_normalized
        
        # Calculate perpendicular distance
        perpendicular = hip_to_knee - projection
        perpendicular_distance = np.linalg.norm(perpendicular)
        
        # Check if knee is tracking properly (within 15% of leg length)
        acceptable_distance = hip_to_ankle_length * 0.15
        return perpendicular_distance <= acceptable_distance
    
    def _check_back_leg_position(self, hip, knee, ankle):
        """
        Check if the back leg is positioned properly.
        
        Args:
            hip: Hip landmark coordinates.
            knee: Knee landmark coordinates.
            ankle: Ankle landmark coordinates.
            
        Returns:
            bool: True if back leg is positioned properly.
        """
        # For back leg, we want knee pointing downward
        hip_to_knee = np.array([knee[0] - hip[0], knee[1] - hip[1]])
        knee_to_ankle = np.array([ankle[0] - knee[0], ankle[1] - knee[1]])
        
        # Calculate angle between these vectors
        def angle_between(v1, v2):
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
            if mag1 * mag2 == 0:
                return 0  # Avoid division by zero
            cos_angle = dot / (mag1 * mag2)
            cos_angle = min(1.0, max(-1.0, cos_angle))  # Clamp to [-1, 1]
            angle = np.arccos(cos_angle)
            return np.degrees(angle)
        
        # Get angle
        leg_angle = angle_between(hip_to_knee, knee_to_ankle)
        
        # For proper back leg position, angle should be around 160-180 degrees
        return leg_angle >= 160
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """Get the comprehensive analysis result with exercise-specific state."""
        result = super().get_analysis_result()
        result['exercise_state'] = self.lunge_state.name
        return result