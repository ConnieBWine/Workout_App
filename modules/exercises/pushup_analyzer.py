"""
Pushup exercise analyzer module.

This module provides functionality to analyze pushup form using pose landmarks.
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import mediapipe as mp

from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackPriority


class PushupState(Enum):
    """States for the pushup exercise."""
    IDLE = 0
    PUSHUP_START = 1
    PUSHUP_DOWN = 2
    PUSHUP_HOLD = 3
    PUSHUP_UP = 4


class PushupAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for pushup exercise form.
    
    Tracks elbow angles, body alignment, and hip position to provide 
    feedback on pushup form.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the pushup analyzer.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score.
        """
        super().__init__(thresholds, visibility_threshold)
        
        # Initialize pushup specific variables
        self.pushup_state = PushupState.IDLE
        self.prev_elbow_angle = 180
        
        # Thresholds specific to pushup
        self.start_threshold = 160    # Arms are almost straight
        self.pushup_threshold = 110   # Arms are bent for a proper pushup
        
        # Tracking for form issues
        self.start_hip_height = None
        self.lowest_shoulder_height = None
        self.max_hip_sag = 0          # Track hip sagging
        self.max_elbow_flare = 0      # Track elbow flaring
        self.min_elbow_angle = 180    # Track lowest elbow angle
        self.max_neck_deviation = 0   # Track neck alignment issues
        
        # Body alignment tracking
        self.alignment_issues = 0
        self.max_alignment_issues = 5
    
    def reset(self):
        """Reset the analyzer state."""
        super().reset()
        self.pushup_state = PushupState.IDLE
        self.prev_elbow_angle = 180
        self.start_hip_height = None
        self.lowest_shoulder_height = None
        self.max_hip_sag = 0
        self.max_elbow_flare = 0
        self.min_elbow_angle = 180
        self.max_neck_deviation = 0
        self.alignment_issues = 0
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], frame_time: float) -> Dict[str, Any]:
        """
        Process detected landmarks to analyze pushup form.
        
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
        left_ankle = self.get_visible_point(landmarks, mp_pose.LEFT_ANKLE.value)
        right_ankle = self.get_visible_point(landmarks, mp_pose.RIGHT_ANKLE.value)
        nose = self.get_visible_point(landmarks, mp_pose.NOSE.value)
        
        # Check if we have enough visible landmarks
        upper_body_visible = all(
            p[2] >= self.visibility_threshold for p in 
            [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist]
        )
        
        body_visible = upper_body_visible and all(
            p[2] >= self.visibility_threshold for p in 
            [left_hip, right_hip, left_ankle, right_ankle]
        )
        
        if not upper_body_visible:
            # Not enough landmarks visible for analysis
            self.feedback_manager.add_feedback(
                "Please position yourself so your upper body is visible", 
                FeedbackPriority.HIGH
            )
            return self.get_analysis_result()
        
        # Calculate key angles
        left_elbow_angle = self.angle_calculator.angle_deg(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = self.angle_calculator.angle_deg(right_shoulder, right_elbow, right_wrist)
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        # Calculate body alignment - from ankles through hips to shoulders (should be straight)
        body_alignment = self._check_body_alignment(
            left_ankle, right_ankle, left_hip, right_hip, left_shoulder, right_shoulder
        )
        
        # Calculate hip sag (how much the hips drop below the line from shoulders to ankles)
        hip_sag = self._calculate_hip_sag(
            left_ankle, right_ankle, left_hip, right_hip, left_shoulder, right_shoulder
        )
        
        # Calculate elbow flare (elbows should be close to body)
        elbow_flare = self._calculate_elbow_flare(
            left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist
        )
        
        # Calculate neck alignment (head should be in line with spine)
        neck_alignment = self._calculate_neck_alignment(
            nose, left_shoulder, right_shoulder, left_hip, right_hip
        )
        
        # Update angle history for smoothing
        self.update_angle_history("elbow_angle", elbow_angle)
        
        # Process the pushup state
        self._process_pushup_state(elbow_angle)
        
        # Analyze form for the current state
        feedback = self._analyze_pushup_form(
            elbow_angle, body_alignment, hip_sag, elbow_flare, neck_alignment
        )
        
        # Update previous angle
        self.prev_elbow_angle = elbow_angle
        
        # Track shoulder height for depth analysis
        shoulder_height = (left_shoulder[1] + right_shoulder[1]) / 2
        if self.lowest_shoulder_height is None or shoulder_height > self.lowest_shoulder_height:
            self.lowest_shoulder_height = shoulder_height
        
        # Track hip height for alignment
        hip_height = (left_hip[1] + right_hip[1]) / 2
        if self.start_hip_height is None or self.pushup_state == PushupState.IDLE:
            self.start_hip_height = hip_height
        
        # Update form tracking variables
        self.min_elbow_angle = min(self.min_elbow_angle, elbow_angle)
        self.max_hip_sag = max(self.max_hip_sag, hip_sag)
        self.max_elbow_flare = max(self.max_elbow_flare, elbow_flare)
        self.max_neck_deviation = max(self.max_neck_deviation, neck_alignment)
        
        # Update the feedback manager frame counter
        self.feedback_manager.update_frame_counter()
        
        # Return result
        result = self.get_analysis_result()
        result.update({
            'exercise_state': self.pushup_state.name,
            'elbow_angle': round(elbow_angle, 1),
            'hip_sag': round(hip_sag, 1),
            'elbow_flare': round(elbow_flare, 1),
            'neck_alignment': round(neck_alignment, 1),
            'body_alignment': round(body_alignment, 2),
        })
        
        return result
    
    def _process_pushup_state(self, elbow_angle: float):
        """
        Process the pushup state based on the current angle.
        
        Args:
            elbow_angle: Current average elbow angle in degrees.
        """
        if self.pushup_state == PushupState.IDLE:
            if elbow_angle < self.start_threshold:
                self.pushup_state = PushupState.PUSHUP_START
                self.feedback_manager.clear_feedback()
                self.form_issues_in_current_rep = False
                self.start_rep()
        
        elif self.pushup_state == PushupState.PUSHUP_START:
            if elbow_angle < self.pushup_threshold:
                self.pushup_state = PushupState.PUSHUP_DOWN
            elif elbow_angle > self.prev_elbow_angle:
                # Going back up without completing the pushup
                self.pushup_state = PushupState.IDLE
                self.feedback_manager.add_feedback(
                    "Lower yourself into a proper pushup", FeedbackPriority.MEDIUM
                )
        
        elif self.pushup_state == PushupState.PUSHUP_DOWN:
            if elbow_angle <= self.prev_elbow_angle:
                self.pushup_state = PushupState.PUSHUP_HOLD
            
        elif self.pushup_state == PushupState.PUSHUP_HOLD:
            if elbow_angle > self.prev_elbow_angle:
                self.pushup_state = PushupState.PUSHUP_UP
                # Analyze the deepest point of the pushup
                self._analyze_pushup_depth()
        
        elif self.pushup_state == PushupState.PUSHUP_UP:
            if elbow_angle >= self.start_threshold:
                self.pushup_state = PushupState.IDLE
                self.increment_rep_counter()
                
                # Add positive feedback if no form issues detected
                if not self.form_issues_in_current_rep:
                    self.feedback_manager.add_feedback(
                        "Excellent pushup form!", FeedbackPriority.LOW
                    )
    
    def _analyze_pushup_form(self, elbow_angle, body_alignment, hip_sag, elbow_flare, neck_alignment):
        """
        Analyze pushup form and generate feedback.
        
        Args:
            elbow_angle: Average angle of both elbows.
            body_alignment: Measure of body straightness (0-1).
            hip_sag: Amount of hip sag (higher values are worse).
            elbow_flare: Measure of elbow flaring (higher values are worse).
            neck_alignment: Measure of neck deviation (higher values are worse).
            
        Returns:
            List of feedback strings.
        """
        has_issues = False
        
        # Only analyze form when in an active pushup state
        if self.pushup_state not in [PushupState.PUSHUP_DOWN, PushupState.PUSHUP_HOLD, PushupState.PUSHUP_UP]:
            return []
        
        # Check pushup depth
        if self.pushup_state == PushupState.PUSHUP_HOLD:
            if elbow_angle > self.thresholds['pushup_not_low_enough']:
                self.feedback_manager.add_feedback(
                    "Lower your chest more for a complete pushup", FeedbackPriority.HIGH
                )
                has_issues = True
        
        # Check hip position (no sagging or raising)
        if hip_sag > self.thresholds['pushup_hip_sag']:
            self.feedback_manager.add_feedback(
                "Keep your body straight, don't let your hips sag", FeedbackPriority.HIGH
            )
            has_issues = True
        elif hip_sag < -self.thresholds['pushup_hip_sag']:
            self.feedback_manager.add_feedback(
                "Keep your body straight, don't raise your hips", FeedbackPriority.MEDIUM
            )
            has_issues = True
        
        # Check elbow position (elbows should be close to body)
        if elbow_flare > self.thresholds['pushup_elbow_flare']:
            self.feedback_manager.add_feedback(
                "Keep your elbows closer to your body", FeedbackPriority.MEDIUM
            )
            has_issues = True
        
        # Check neck position (look at floor slightly ahead, not down or up)
        if neck_alignment > self.thresholds['pushup_neck_alignment']:
            self.feedback_manager.add_feedback(
                "Keep your neck neutral, look at the floor ahead of you", FeedbackPriority.LOW
            )
            has_issues = True
        
        # Check overall body alignment
        if body_alignment < 0.7:  # Arbitrary threshold for good alignment
            self.alignment_issues += 1
            
            if self.alignment_issues >= self.max_alignment_issues:
                self.feedback_manager.add_feedback(
                    "Maintain a straight line from head to heels", FeedbackPriority.HIGH
                )
                self.alignment_issues = 0
                has_issues = True
        else:
            self.alignment_issues = 0
        
        # Update form issues flag
        if has_issues:
            self.form_issues_in_current_rep = True
        
        return self.feedback_manager.get_feedback()
    
    def _analyze_pushup_depth(self):
        """Analyze the depth of the pushup at its lowest point."""
        if self.min_elbow_angle > self.thresholds['pushup_not_low_enough']:
            self.feedback_manager.add_feedback(
                "Try to go deeper in your pushups", FeedbackPriority.MEDIUM
            )
    
    def _check_body_alignment(self, left_ankle, right_ankle, left_hip, right_hip, 
                             left_shoulder, right_shoulder):
        """
        Check if the body is in a straight line from ankles to shoulders.
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Alignment score (0-1, where 1 is perfect alignment).
        """
        # Get midpoints
        ankle_mid = [(left_ankle[0] + right_ankle[0]) / 2, (left_ankle[1] + right_ankle[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2]
        
        # Calculate the line from ankles to shoulders
        line_vector = [shoulder_mid[0] - ankle_mid[0], shoulder_mid[1] - ankle_mid[1]]
        line_length = np.sqrt(line_vector[0]**2 + line_vector[1]**2)
        
        if line_length == 0:
            return 1.0  # Avoid division by zero
            
        normalized_line = [line_vector[0] / line_length, line_vector[1] / line_length]
        
        # Calculate hip deviation from the line
        hip_to_ankle = [hip_mid[0] - ankle_mid[0], hip_mid[1] - ankle_mid[1]]
        
        # Project hip_to_ankle onto the line
        projection = (hip_to_ankle[0] * normalized_line[0] + 
                     hip_to_ankle[1] * normalized_line[1])
        
        # Calculate the point on the line
        point_on_line = [
            ankle_mid[0] + projection * normalized_line[0],
            ankle_mid[1] + projection * normalized_line[1]
        ]
        
        # Calculate perpendicular distance
        hip_deviation = np.sqrt((hip_mid[0] - point_on_line[0])**2 + 
                               (hip_mid[1] - point_on_line[1])**2)
        
        # Normalize by body length
        alignment_score = 1.0 - (hip_deviation / line_length)
        return max(0.0, min(1.0, alignment_score))  # Clip to [0,1]
    
    def _calculate_hip_sag(self, left_ankle, right_ankle, left_hip, right_hip, 
                          left_shoulder, right_shoulder):
        """
        Calculate the amount of hip sag (positive) or raising (negative).
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Hip sag value (positive for sagging, negative for raising).
        """
        # Get midpoints
        ankle_mid = [(left_ankle[0] + right_ankle[0]) / 2, (left_ankle[1] + right_ankle[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2]
        
        # For a pushup, we need to normalize for the camera perspective
        # assuming camera is viewing from the side
        
        # Calculate the expected hip position (should be on straight line)
        total_length = np.sqrt((shoulder_mid[0] - ankle_mid[0])**2 + 
                              (shoulder_mid[1] - ankle_mid[1])**2)
        
        # Approximate the ratio of hip position on the line
        hip_to_ankle_ratio = 0.6  # Typical ratio based on body proportions
        
        # Expected hip position on the line
        expected_hip = [
            ankle_mid[0] + hip_to_ankle_ratio * (shoulder_mid[0] - ankle_mid[0]),
            ankle_mid[1] + hip_to_ankle_ratio * (shoulder_mid[1] - ankle_mid[1])
        ]
        
        # Calculate vertical difference (in pushup context)
        # Positive means hips are lower than expected (sagging)
        # Negative means hips are higher than expected (raising)
        hip_sag = hip_mid[1] - expected_hip[1]
        
        # Normalize by body length
        normalized_sag = hip_sag / total_length * 100  # Convert to percentage
        
        return normalized_sag
    
    def _calculate_elbow_flare(self, left_shoulder, right_shoulder, 
                              left_elbow, right_elbow, 
                              left_wrist, right_wrist):
        """
        Calculate the amount of elbow flaring (elbows away from body).
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Elbow flare value (higher is worse).
        """
        # For ideal pushup, elbows should be at about 45 degrees from body
        # Calculate projected angles from top-down view
        
        # Left arm
        left_shoulder_to_elbow = [left_elbow[0] - left_shoulder[0], left_elbow[1] - left_shoulder[1]]
        left_elbow_to_wrist = [left_wrist[0] - left_elbow[0], left_wrist[1] - left_elbow[1]]
        
        # Right arm
        right_shoulder_to_elbow = [right_elbow[0] - right_shoulder[0], right_elbow[1] - right_shoulder[1]]
        right_elbow_to_wrist = [right_wrist[0] - right_elbow[0], right_wrist[1] - right_elbow[1]]
        
        # Calculate angles between vectors (simplified for 2D)
        def angle_between(v1, v2):
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
            cos_angle = dot / (mag1 * mag2)
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
            return np.degrees(angle)
        
        # Get angles
        left_arm_angle = angle_between(left_shoulder_to_elbow, left_elbow_to_wrist)
        right_arm_angle = angle_between(right_shoulder_to_elbow, right_elbow_to_wrist)
        
        # Average angle difference from ideal (45 degrees)
        ideal_angle = 45
        flare_score = abs((left_arm_angle + right_arm_angle) / 2 - ideal_angle)
        
        return flare_score
    
    def _calculate_neck_alignment(self, nose, left_shoulder, right_shoulder, 
                                 left_hip, right_hip):
        """
        Calculate the alignment of the neck relative to the spine.
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Neck alignment deviation (higher is worse).
        """
        # Get midpoints
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
        
        # Calculate spine direction
        spine_vector = [shoulder_mid[0] - hip_mid[0], shoulder_mid[1] - hip_mid[1]]
        spine_length = np.sqrt(spine_vector[0]**2 + spine_vector[1]**2)
        
        if spine_length == 0:
            return 0.0  # Avoid division by zero
            
        normalized_spine = [spine_vector[0] / spine_length, spine_vector[1] / spine_length]
        
        # Calculate neck direction (shoulder to nose)
        neck_vector = [nose[0] - shoulder_mid[0], nose[1] - shoulder_mid[1]]
        neck_length = np.sqrt(neck_vector[0]**2 + neck_vector[1]**2)
        
        if neck_length == 0:
            return 0.0  # Avoid division by zero
            
        normalized_neck = [neck_vector[0] / neck_length, neck_vector[1] / neck_length]
        
        # Calculate angle between spine and neck
        dot_product = normalized_spine[0] * normalized_neck[0] + normalized_spine[1] * normalized_neck[1]
        angle = np.arccos(np.clip(dot_product, -1.0, 1.0))
        angle_degrees = np.degrees(angle)
        
        # Normalize: 0 means perfect alignment, higher values mean worse alignment
        # For a good pushup, neck should be roughly in line with spine
        return abs(angle_degrees)
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """Get the current analysis result."""
        result = super().get_analysis_result()
        result['exercise_state'] = self.pushup_state.name
        return result