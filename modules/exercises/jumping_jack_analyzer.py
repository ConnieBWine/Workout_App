"""
Jumping jack exercise analyzer module.

This module provides comprehensive analysis of jumping jack exercises using pose landmarks,
detecting form issues such as inadequate arm extension, insufficient leg spread, and
asymmetrical movements. Jumping jacks can be analyzed both as a rep-based exercise
and as a timed exercise for cardio purposes.
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import mediapipe as mp
import time

from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackPriority


class JumpingJackState(Enum):
    """States for tracking jumping jack exercise progression."""
    IDLE = 0
    STARTING = 1
    ARMS_LEGS_UP = 2
    ARMS_LEGS_DOWN = 3


class JumpingJackAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for jumping jack exercise form.
    
    Tracks arm extension, leg spread, symmetry, and timing to provide
    comprehensive feedback on jumping jack form and performance.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the jumping jack analyzer with form thresholds and visibility requirements.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score to consider points valid.
        """
        super().__init__(thresholds, visibility_threshold)
        
        # Jumping jacks can be either rep-based or timed
        self.is_timed_exercise = False  # Can be changed via set_timed_exercise
        
        # Initialize jumping jack-specific state variables
        self.jumping_jack_state = JumpingJackState.IDLE
        
        # Form tracking variables
        self.arm_extension = 0     # 0-1 where 1 is full extension
        self.leg_spread = 0        # 0-1 where 1 is full spread
        self.symmetry_score = 1.0  # 1.0 is perfect symmetry
        self.pace_consistency = 1.0  # 1.0 is perfectly consistent pace
        
        # Timing variables
        self.last_rep_time = None
        self.rep_durations = []
        self.target_rep_duration = 1.0  # Target of 1 second per rep
        
        # Performance tracking
        self.arms_not_extended_enough_count = 0
        self.legs_not_spread_enough_count = 0
        self.asymmetrical_movement_count = 0
        self.pace_issues_count = 0
        
        # Rep tracking 
        self.last_state_change_time = None
        self.state_durations = {state: [] for state in JumpingJackState}
        
        # Initialize smoothing buffers
        self.arm_extension_buffer = []
        self.leg_spread_buffer = []
        self.symmetry_buffer = []
    
    def reset(self):
        """Reset the analyzer state for a new exercise sequence."""
        super().reset()
        self.jumping_jack_state = JumpingJackState.IDLE
        self.arm_extension = 0
        self.leg_spread = 0
        self.symmetry_score = 1.0
        self.pace_consistency = 1.0
        self.last_rep_time = None
        self.rep_durations = []
        self.arms_not_extended_enough_count = 0
        self.legs_not_spread_enough_count = 0
        self.asymmetrical_movement_count = 0
        self.pace_issues_count = 0
        self.last_state_change_time = None
        self.state_durations = {state: [] for state in JumpingJackState}
        self.arm_extension_buffer = []
        self.leg_spread_buffer = []
        self.symmetry_buffer = []
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], frame_time: float) -> Dict[str, Any]:
        """
        Process detected landmarks to analyze jumping jack form with high precision.
        
        Args:
            landmarks: Dictionary of detected landmarks from pose detector.
            frame_time: Time delta since last frame in seconds.
            
        Returns:
            Dictionary of comprehensive analysis results including movement metrics and feedback.
        """
        mp_pose = mp.solutions.pose.PoseLandmark
        
        # Extract required landmarks for jumping jack analysis
        left_shoulder = self.get_visible_point(landmarks, mp_pose.LEFT_SHOULDER.value)
        right_shoulder = self.get_visible_point(landmarks, mp_pose.RIGHT_SHOULDER.value)
        left_elbow = self.get_visible_point(landmarks, mp_pose.LEFT_ELBOW.value)
        right_elbow = self.get_visible_point(landmarks, mp_pose.RIGHT_ELBOW.value)
        left_wrist = self.get_visible_point(landmarks, mp_pose.LEFT_WRIST.value)
        right_wrist = self.get_visible_point(landmarks, mp_pose.RIGHT_WRIST.value)
        left_hip = self.get_visible_point(landmarks, mp_pose.LEFT_HIP.value)
        right_hip = self.get_visible_point(landmarks, mp_pose.RIGHT_HIP.value)
        left_knee = self.get_visible_point(landmarks, mp_pose.LEFT_KNEE.value)
        right_knee = self.get_visible_point(landmarks, mp_pose.RIGHT_KNEE.value)
        left_ankle = self.get_visible_point(landmarks, mp_pose.LEFT_ANKLE.value)
        right_ankle = self.get_visible_point(landmarks, mp_pose.RIGHT_ANKLE.value)
        
        # Check if we have enough visible landmarks for proper analysis
        upper_body_visible = all(
            p[2] >= self.visibility_threshold for p in 
            [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist]
        )
        
        lower_body_visible = all(
            p[2] >= self.visibility_threshold for p in 
            [left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]
        )
        
        if not upper_body_visible and not lower_body_visible:
            # Not enough landmarks visible for analysis
            self.feedback_manager.add_feedback(
                "Please position yourself so your full body is visible", 
                FeedbackPriority.HIGH
            )
            return self.get_analysis_result()
        
        # Calculate key movement metrics
        
        # 1. Calculate arm extension
        arm_extension = 0
        if upper_body_visible:
            arm_extension = self._calculate_arm_extension(
                left_shoulder, right_shoulder, 
                left_elbow, right_elbow,
                left_wrist, right_wrist
            )
            
            # Smooth arm extension using a buffer
            self.arm_extension_buffer.append(arm_extension)
            if len(self.arm_extension_buffer) > 5:
                self.arm_extension_buffer.pop(0)
            
            self.arm_extension = sum(self.arm_extension_buffer) / len(self.arm_extension_buffer)
        
        # 2. Calculate leg spread
        leg_spread = 0
        if lower_body_visible:
            leg_spread = self._calculate_leg_spread(
                left_hip, right_hip,
                left_ankle, right_ankle
            )
            
            # Smooth leg spread using a buffer
            self.leg_spread_buffer.append(leg_spread)
            if len(self.leg_spread_buffer) > 5:
                self.leg_spread_buffer.pop(0)
            
            self.leg_spread = sum(self.leg_spread_buffer) / len(self.leg_spread_buffer)
        
        # 3. Calculate movement symmetry
        symmetry = 1.0
        if upper_body_visible and lower_body_visible:
            symmetry = self._calculate_symmetry(
                left_shoulder, right_shoulder,
                left_wrist, right_wrist,
                left_ankle, right_ankle
            )
            
            # Smooth symmetry using a buffer
            self.symmetry_buffer.append(symmetry)
            if len(self.symmetry_buffer) > 5:
                self.symmetry_buffer.pop(0)
            
            self.symmetry_score = sum(self.symmetry_buffer) / len(self.symmetry_buffer)
        
        # Determine jumping jack state based on current metrics
        previous_state = self.jumping_jack_state
        self._update_jumping_jack_state(self.arm_extension, self.leg_spread)
        
        # Update timing metrics if state changed
        current_time = time.time()
        if self.jumping_jack_state != previous_state:
            if self.last_state_change_time is not None:
                duration = current_time - self.last_state_change_time
                self.state_durations[previous_state].append(duration)
                
                # If we completed a full rep (back to down position)
                if self.jumping_jack_state == JumpingJackState.ARMS_LEGS_DOWN and previous_state == JumpingJackState.ARMS_LEGS_UP:
                    if self.last_rep_time is not None:
                        rep_duration = current_time - self.last_rep_time
                        self.rep_durations.append(rep_duration)
                        
                        # Keep only the last 5 rep durations for consistency calculation
                        if len(self.rep_durations) > 5:
                            self.rep_durations.pop(0)
                        
                        self._update_pace_consistency()
                    
                    self.last_rep_time = current_time
                    self.increment_rep_counter()
            
            self.last_state_change_time = current_time
        
        # Generate appropriate feedback based on current form
        feedback = self._generate_feedback()
        
        # Update the feedback manager frame counter
        self.feedback_manager.update_frame_counter()
        
        # Update accumulated time if active and in timed mode
        if self.timer_active and self.is_timed_exercise:
            self.time_accumulated += frame_time
        
        # Return comprehensive analysis result
        result = self.get_analysis_result()
        result.update({
            'exercise_state': self.jumping_jack_state.name,
            'arm_extension': round(self.arm_extension, 2),
            'leg_spread': round(self.leg_spread, 2),
            'symmetry_score': round(self.symmetry_score, 2),
            'pace_consistency': round(self.pace_consistency, 2),
            'avg_rep_duration': round(self._get_average_rep_duration(), 2) if self.rep_durations else 0,
        })
        
        return result
    
    def _update_jumping_jack_state(self, arm_extension: float, leg_spread: float):
        """
        Update the jumping jack state based on current arm and leg positions.
        
        Args:
            arm_extension: Measure of arm extension (0-1).
            leg_spread: Measure of leg spread (0-1).
        """
        # Thresholds for state transitions
        up_threshold = 0.7    # Threshold for considering arms/legs up
        down_threshold = 0.3  # Threshold for considering arms/legs down
        
        if self.jumping_jack_state == JumpingJackState.IDLE:
            # Starting position should have arms and legs down
            if arm_extension < down_threshold and leg_spread < down_threshold:
                self.jumping_jack_state = JumpingJackState.STARTING
                self.feedback_manager.clear_feedback()
                self.timer_active = True
        
        elif self.jumping_jack_state == JumpingJackState.STARTING:
            # Transition to arms/legs up position
            if arm_extension > up_threshold and leg_spread > up_threshold:
                self.jumping_jack_state = JumpingJackState.ARMS_LEGS_UP
        
        elif self.jumping_jack_state == JumpingJackState.ARMS_LEGS_UP:
            # Transition to arms/legs down position
            if arm_extension < down_threshold and leg_spread < down_threshold:
                self.jumping_jack_state = JumpingJackState.ARMS_LEGS_DOWN
        
        elif self.jumping_jack_state == JumpingJackState.ARMS_LEGS_DOWN:
            # Either go back to arms/legs up for another rep
            if arm_extension > up_threshold and leg_spread > up_threshold:
                self.jumping_jack_state = JumpingJackState.ARMS_LEGS_UP
            # Or if there's a pause, go back to starting position
            elif arm_extension < down_threshold and leg_spread < down_threshold:
                # Stay in down position
                pass
    
    def _generate_feedback(self) -> List[str]:
        """
        Generate appropriate feedback based on current form issues.
        
        Returns:
            List of feedback strings ordered by priority.
        """
        # Only provide detailed feedback when actively doing jumping jacks
        if self.jumping_jack_state == JumpingJackState.IDLE:
            return []
        
        has_issues = False
        
        # Check arm extension
        if self.jumping_jack_state == JumpingJackState.ARMS_LEGS_UP and self.arm_extension < 0.8:
            self.arms_not_extended_enough_count += 1
            
            if self.arms_not_extended_enough_count >= 3:
                self.feedback_manager.add_feedback(
                    "Extend your arms fully above your head", 
                    FeedbackPriority.MEDIUM
                )
                self.arms_not_extended_enough_count = 0
                has_issues = True
        else:
            self.arms_not_extended_enough_count = 0
        
        # Check leg spread
        if self.jumping_jack_state == JumpingJackState.ARMS_LEGS_UP and self.leg_spread < 0.7:
            self.legs_not_spread_enough_count += 1
            
            if self.legs_not_spread_enough_count >= 3:
                self.feedback_manager.add_feedback(
                    "Jump wider with your legs", 
                    FeedbackPriority.MEDIUM
                )
                self.legs_not_spread_enough_count = 0
                has_issues = True
        else:
            self.legs_not_spread_enough_count = 0
        
        # Check symmetry
        if self.symmetry_score < 0.8:
            self.asymmetrical_movement_count += 1
            
            if self.asymmetrical_movement_count >= 3:
                self.feedback_manager.add_feedback(
                    "Keep your movements symmetrical on both sides", 
                    FeedbackPriority.LOW
                )
                self.asymmetrical_movement_count = 0
                has_issues = True
        else:
            self.asymmetrical_movement_count = 0
        
        # Check pace consistency
        if self.pace_consistency < 0.8 and len(self.rep_durations) >= 3:
            self.pace_issues_count += 1
            
            if self.pace_issues_count >= 2:
                avg_duration = self._get_average_rep_duration()
                if avg_duration > 1.5:
                    self.feedback_manager.add_feedback(
                        "Try to maintain a faster, consistent pace", 
                        FeedbackPriority.LOW
                    )
                elif avg_duration < 0.5:
                    self.feedback_manager.add_feedback(
                        "Slow down slightly for better form", 
                        FeedbackPriority.LOW
                    )
                else:
                    self.feedback_manager.add_feedback(
                        "Try to maintain a consistent pace", 
                        FeedbackPriority.LOW
                    )
                self.pace_issues_count = 0
                has_issues = True
        else:
            self.pace_issues_count = 0
        
        # Positive feedback for good form
        if not has_issues and self.rep_counter > 2:
            self.feedback_manager.add_feedback(
                "Good jumping jack form, keep it up!", 
                FeedbackPriority.LOW
            )
        
        return self.feedback_manager.get_feedback()
    
    def _calculate_arm_extension(self, left_shoulder, right_shoulder, 
                               left_elbow, right_elbow,
                               left_wrist, right_wrist):
        """
        Calculate the degree of arm extension during jumping jacks.
        
        Args:
            Various upper body landmarks.
            
        Returns:
            float: Arm extension score (0-1, where 1 is full extension).
        """
        # For jumping jacks, we're interested in:
        # 1. Arms raised above head (shoulder-to-wrist vertical angle)
        # 2. Arms fully extended (shoulder-elbow-wrist angle)
        
        # Calculate vertical angle for each arm (0 = down, 180 = up)
        left_vertical = 180 - self.angle_calculator.calculate_vertical_angle(
            left_shoulder[:2], left_wrist[:2]
        )
        right_vertical = 180 - self.angle_calculator.calculate_vertical_angle(
            right_shoulder[:2], right_wrist[:2]
        )
        
        # Calculate arm straightness
        left_arm_angle = self.angle_calculator.angle_deg(
            left_shoulder, left_elbow, left_wrist
        )
        right_arm_angle = self.angle_calculator.angle_deg(
            right_shoulder, right_elbow, right_wrist
        )
        
        # Normalize vertical position (0 = down by side, 1 = fully above head)
        vertical_score = (left_vertical + right_vertical) / 360
        vertical_score = min(1.0, max(0.0, vertical_score))
        
        # Normalize arm straightness (0 = bent, 1 = straight)
        # Arms should be straight in jumping jacks, so closer to 180 is better
        straightness_score = (left_arm_angle + right_arm_angle) / 360
        straightness_score = min(1.0, max(0.0, straightness_score))
        
        # Combine scores (weighted toward vertical position)
        return 0.7 * vertical_score + 0.3 * straightness_score
    
    def _calculate_leg_spread(self, left_hip, right_hip, 
                             left_ankle, right_ankle):
        """
        Calculate the degree of leg spread during jumping jacks.
        
        Args:
            Various lower body landmarks.
            
        Returns:
            float: Leg spread score (0-1, where 1 is full spread).
        """
        # Calculate hip width (distance between left and right hip)
        hip_width = self.angle_calculator.find_distance(
            left_hip[:2], right_hip[:2]
        )
        
        # Calculate ankle spread (distance between left and right ankle)
        ankle_spread = self.angle_calculator.find_distance(
            left_ankle[:2], right_ankle[:2]
        )
        
        # Normalize spread relative to hip width
        # A good jumping jack should have ankles spread to ~2x hip width
        relative_spread = (ankle_spread / hip_width) - 1.0
        
        # Normalize to 0-1 scale
        # 0 = feet together, 1 = good spread (2x hip width or more)
        normalized_spread = min(1.0, max(0.0, relative_spread))
        
        return normalized_spread
    
    def _calculate_symmetry(self, left_shoulder, right_shoulder,
                          left_wrist, right_wrist,
                          left_ankle, right_ankle):
        """
        Calculate the symmetry of movement during jumping jacks.
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Symmetry score (0-1, where 1 is perfectly symmetrical).
        """
        # For symmetry, compare:
        # 1. Vertical position of left vs right wrist
        # 2. Horizontal position of left vs right ankle
        
        # Vertical symmetry of arms
        left_wrist_height = left_wrist[1]
        right_wrist_height = right_wrist[1]
        wrist_height_diff = abs(left_wrist_height - right_wrist_height)
        
        # Normalize by shoulder height difference (to account for camera angle)
        shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1])
        normalized_wrist_diff = wrist_height_diff - shoulder_height_diff
        
        # Horizontal symmetry of ankles
        shoulder_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
        left_ankle_offset = abs(left_ankle[0] - shoulder_center_x)
        right_ankle_offset = abs(right_ankle[0] - shoulder_center_x)
        ankle_offset_diff = abs(left_ankle_offset - right_ankle_offset)
        
        # Normalize differences to 0-1 scale
        # Smaller differences = higher symmetry
        arm_symmetry = 1.0 - min(1.0, normalized_wrist_diff * 5)
        leg_symmetry = 1.0 - min(1.0, ankle_offset_diff * 5)
        
        # Combine scores
        return (arm_symmetry + leg_symmetry) / 2
    
    def _update_pace_consistency(self):
        """Update the pace consistency score based on recent rep durations."""
        if len(self.rep_durations) < 2:
            self.pace_consistency = 1.0
            return
        
        # Calculate average and standard deviation
        avg_duration = sum(self.rep_durations) / len(self.rep_durations)
        variance = sum((d - avg_duration) ** 2 for d in self.rep_durations) / len(self.rep_durations)
        std_dev = variance ** 0.5
        
        # Calculate coefficient of variation (standard deviation / mean)
        # Lower CV = more consistent
        cv = std_dev / avg_duration if avg_duration > 0 else 0
        
        # Convert to a 0-1 score where 1 is perfectly consistent
        # CV of 0.2 or less is considered good consistency
        self.pace_consistency = 1.0 - min(1.0, cv / 0.2)
    
    def _get_average_rep_duration(self):
        """Get the average duration of recent reps."""
        if not self.rep_durations:
            return 0
        return sum(self.rep_durations) / len(self.rep_durations)
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """Get the comprehensive analysis result with exercise-specific state."""
        result = super().get_analysis_result()
        result['exercise_state'] = self.jumping_jack_state.name
        return result