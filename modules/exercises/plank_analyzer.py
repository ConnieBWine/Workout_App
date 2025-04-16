"""
Plank exercise analyzer module.

This module provides comprehensive analysis of plank form using pose landmarks,
detecting common form issues such as hip sagging, hip raising, and head alignment problems.
As plank is a timed exercise, this analyzer focuses on sustained quality of form rather
than repetition counting.
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import mediapipe as mp

from modules.exercise_analyzer import ExerciseAnalyzer
from modules.feedback_manager import FeedbackPriority


class PlankState(Enum):
    """States for tracking plank exercise status."""
    IDLE = 0
    STARTING = 1
    HOLDING = 2
    ENDING = 3


class PlankAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for plank exercise form.
    
    Tracks body alignment, hip position, shoulder stability, and head alignment
    to provide comprehensive feedback on plank form during the timed exercise.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the plank analyzer with form thresholds and visibility requirements.
        
        Args:
            thresholds: Dictionary of threshold values for form analysis.
            visibility_threshold: Minimum landmark visibility score to consider points valid.
        """
        super().__init__(thresholds, visibility_threshold)
        
        # Set as timed exercise
        self.is_timed_exercise = True
        
        # Initialize plank-specific state variables
        self.plank_state = PlankState.IDLE
        
        # Form tracking variables
        self.hip_position = 0       # 0 = aligned, negative = sagging, positive = elevated
        self.body_alignment = 1.0   # 1.0 = perfect, lower values indicate worse alignment
        self.elbow_shoulder_alignment = 1.0  # Alignment of elbows relative to shoulders
        self.head_alignment = 0     # Deviation from neutral neck position
        
        # Timing variables
        self.hold_start_time = None
        self.good_form_duration = 0
        self.last_frame_time = None
        
        # Form issue tracking
        self.hip_sag_time = 0
        self.hip_pike_time = 0
        self.body_misalignment_time = 0
        self.head_misalignment_time = 0
        
        # Stability tracking
        self.position_history = []
        self.stability_score = 1.0
        
        # Initialize smoothing buffers
        self.hip_position_buffer = []
        self.body_alignment_buffer = []
        self.head_alignment_buffer = []
    
    def reset(self):
        """Reset the analyzer state for a new exercise sequence."""
        super().reset()
        self.plank_state = PlankState.IDLE
        self.hip_position = 0
        self.body_alignment = 1.0
        self.elbow_shoulder_alignment = 1.0
        self.head_alignment = 0
        self.hold_start_time = None
        self.good_form_duration = 0
        self.hip_sag_time = 0
        self.hip_pike_time = 0
        self.body_misalignment_time = 0
        self.head_misalignment_time = 0
        self.position_history = []
        self.stability_score = 1.0
        self.hip_position_buffer = []
        self.body_alignment_buffer = []
        self.head_alignment_buffer = []
        self.timer_active = False
        self.time_accumulated = 0
    
    def analyze_landmarks(self, landmarks: Dict[int, Dict[str, float]], frame_time: float) -> Dict[str, Any]:
        """
        Process detected landmarks to analyze plank form with high precision.
        
        Args:
            landmarks: Dictionary of detected landmarks from pose detector.
            frame_time: Time delta since last frame in seconds.
            
        Returns:
            Dictionary of comprehensive analysis results including alignment metrics and feedback.
        """
        mp_pose = mp.solutions.pose.PoseLandmark
        
        # Extract required landmarks for plank analysis
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
        nose = self.get_visible_point(landmarks, mp_pose.NOSE.value)
        
        # Check if we have enough visible landmarks for proper analysis
        upper_body_visible = all(
            p[2] >= self.visibility_threshold for p in 
            [left_shoulder, right_shoulder, left_elbow, right_elbow]
        )
        
        core_visible = upper_body_visible and all(
            p[2] >= self.visibility_threshold for p in 
            [left_hip, right_hip]
        )
        
        if not upper_body_visible:
            # Not enough landmarks visible for analysis
            self.feedback_manager.add_feedback(
                "Please position yourself so your upper body is visible", 
                FeedbackPriority.HIGH
            )
            return self.get_analysis_result()
        
        # Calculate key body alignment metrics
        
        # 1. Calculate hip position relative to the shoulder-ankle line
        hip_position = 0
        if core_visible and all(p[2] >= self.visibility_threshold for p in [left_ankle, right_ankle]):
            hip_position = self._calculate_hip_position(
                left_shoulder, right_shoulder, 
                left_hip, right_hip, 
                left_ankle, right_ankle
            )
            
            # Smooth hip position using a buffer
            self.hip_position_buffer.append(hip_position)
            if len(self.hip_position_buffer) > 5:
                self.hip_position_buffer.pop(0)
            
            self.hip_position = sum(self.hip_position_buffer) / len(self.hip_position_buffer)
        
        # 2. Calculate overall body alignment (ankles, hips, shoulders should form straight line)
        body_alignment = 1.0
        if core_visible and all(p[2] >= self.visibility_threshold for p in [left_ankle, right_ankle]):
            body_alignment = self._calculate_body_alignment(
                left_ankle, right_ankle, 
                left_hip, right_hip, 
                left_shoulder, right_shoulder
            )
            
            # Smooth body alignment using a buffer
            self.body_alignment_buffer.append(body_alignment)
            if len(self.body_alignment_buffer) > 5:
                self.body_alignment_buffer.pop(0)
            
            self.body_alignment = sum(self.body_alignment_buffer) / len(self.body_alignment_buffer)
        
        # 3. Calculate elbow-shoulder alignment (elbows should be under shoulders)
        if upper_body_visible:
            self.elbow_shoulder_alignment = self._calculate_elbow_shoulder_alignment(
                left_shoulder, right_shoulder, 
                left_elbow, right_elbow
            )
        
        # 4. Calculate head/neck alignment (head should be in neutral position)
        head_alignment = 0
        if upper_body_visible and nose[2] >= self.visibility_threshold:
            head_alignment = self._calculate_head_alignment(
                nose, left_shoulder, right_shoulder, left_hip, right_hip
            )
            
            # Smooth head alignment using a buffer
            self.head_alignment_buffer.append(head_alignment)
            if len(self.head_alignment_buffer) > 5:
                self.head_alignment_buffer.pop(0)
            
            self.head_alignment = sum(self.head_alignment_buffer) / len(self.head_alignment_buffer)
        
        # 5. Calculate stability by tracking movement of reference points
        if core_visible:
            self._update_stability_score(left_shoulder, right_shoulder, left_hip, right_hip)
        
        # Determine plank state based on current metrics
        self._update_plank_state(body_alignment, self.hip_position)
        
        # Track time and analyze form issues
        self._track_time_and_issues(frame_time)
        
        # Generate appropriate feedback based on current form
        feedback = self._generate_feedback()
        
        # Update the feedback manager frame counter
        self.feedback_manager.update_frame_counter()
        
        # Update accumulated time if active
        if self.timer_active:
            self.time_accumulated += frame_time
        
        # Return comprehensive analysis result
        result = self.get_analysis_result()
        result.update({
            'exercise_state': self.plank_state.name,
            'hip_position': round(self.hip_position, 2),
            'body_alignment': round(self.body_alignment, 2),
            'elbow_shoulder_alignment': round(self.elbow_shoulder_alignment, 2),
            'head_alignment': round(self.head_alignment, 2),
            'stability_score': round(self.stability_score, 2),
            'good_form_duration': round(self.good_form_duration, 1),
            'hip_sag_time': round(self.hip_sag_time, 1),
            'hip_pike_time': round(self.hip_pike_time, 1),
        })
        
        return result
    
    def _update_plank_state(self, body_alignment: float, hip_position: float):
        """
        Update the plank state based on current form metrics.
        
        Args:
            body_alignment: Measure of overall body alignment (0-1).
            hip_position: Measure of hip position relative to ideal.
        """
        if self.plank_state == PlankState.IDLE:
            # Detect if user is getting into plank position
            if body_alignment >= 0.75 and abs(hip_position) < 0.2:
                self.plank_state = PlankState.STARTING
                self.feedback_manager.clear_feedback()
                self.timer_active = False
        
        elif self.plank_state == PlankState.STARTING:
            # User is getting into position
            if body_alignment >= 0.85 and abs(hip_position) < 0.15:
                self.plank_state = PlankState.HOLDING
                self.timer_active = True
                self.feedback_manager.add_feedback(
                    "Good plank position, hold steady", FeedbackPriority.LOW
                )
            elif body_alignment < 0.7 or abs(hip_position) > 0.3:
                # User abandoned getting into position
                self.plank_state = PlankState.IDLE
                self.timer_active = False
        
        elif self.plank_state == PlankState.HOLDING:
            # User is holding the plank
            if body_alignment < 0.7 or abs(hip_position) > 0.3:
                # User is losing form or ending the plank
                self.plank_state = PlankState.ENDING
            
        elif self.plank_state == PlankState.ENDING:
            # User is ending the plank
            if body_alignment < 0.6 or abs(hip_position) > 0.4:
                self.plank_state = PlankState.IDLE
                self.timer_active = False
                if self.time_accumulated >= 5.0:  # Only count if held for at least 5 seconds
                    self.increment_rep_counter()  # For tracking completed planks
            elif body_alignment >= 0.85 and abs(hip_position) < 0.15:
                # User recovered form
                self.plank_state = PlankState.HOLDING
    
    def _track_time_and_issues(self, frame_time: float):
        """
        Track time spent in various form conditions.
        
        Args:
            frame_time: Time delta since last frame in seconds.
        """
        # Only track when actively holding plank
        if self.plank_state != PlankState.HOLDING:
            return
        
        # Track good form duration
        if self.body_alignment >= 0.9 and abs(self.hip_position) < 0.1 and abs(self.head_alignment) < 10:
            self.good_form_duration += frame_time
        
        # Track hip sag time
        if self.hip_position < -0.15:  # Negative values indicate sagging
            self.hip_sag_time += frame_time
        
        # Track hip pike time
        if self.hip_position > 0.15:  # Positive values indicate piking (raising)
            self.hip_pike_time += frame_time
        
        # Track body misalignment time
        if self.body_alignment < 0.8:
            self.body_misalignment_time += frame_time
        
        # Track head misalignment time
        if abs(self.head_alignment) > 15:
            self.head_misalignment_time += frame_time
    
    def _generate_feedback(self) -> List[str]:
        """
        Generate appropriate feedback based on current form issues.
        
        Returns:
            List of feedback strings ordered by priority.
        """
        # Only provide feedback when in plank position
        if self.plank_state not in [PlankState.STARTING, PlankState.HOLDING]:
            return []
        
        has_issues = False
        
        # Check hip position
        if self.hip_position < -0.2:  # Hip sagging
            self.feedback_manager.add_feedback(
                "Lift your hips up, don't let them sag", 
                FeedbackPriority.HIGH
            )
            has_issues = True
        elif self.hip_position > 0.2:  # Hip raised too high
            self.feedback_manager.add_feedback(
                "Lower your hips, don't pike up", 
                FeedbackPriority.HIGH
            )
            has_issues = True
        
        # Check body alignment
        if self.body_alignment < 0.75:
            self.feedback_manager.add_feedback(
                "Align your body in a straight line from head to heels", 
                FeedbackPriority.MEDIUM
            )
            has_issues = True
        
        # Check elbow-shoulder alignment
        if self.elbow_shoulder_alignment < 0.7:
            self.feedback_manager.add_feedback(
                "Position your elbows directly under your shoulders", 
                FeedbackPriority.MEDIUM
            )
            has_issues = True
        
        # Check head alignment
        if abs(self.head_alignment) > 20:
            if self.head_alignment > 0:
                self.feedback_manager.add_feedback(
                    "Don't look up, keep your neck neutral", 
                    FeedbackPriority.LOW
                )
            else:
                self.feedback_manager.add_feedback(
                    "Don't look down, keep your neck neutral", 
                    FeedbackPriority.LOW
                )
            has_issues = True
        
        # Check stability
        if self.stability_score < 0.7:
            self.feedback_manager.add_feedback(
                "Try to hold more steady, minimize movement", 
                FeedbackPriority.LOW
            )
            has_issues = True
        
        # Positive feedback for good form
        if not has_issues and self.plank_state == PlankState.HOLDING:
            self.feedback_manager.add_feedback(
                "Excellent plank form, keep it up!", 
                FeedbackPriority.LOW
            )
        
        return self.feedback_manager.get_feedback()
    
    def _calculate_hip_position(self, left_shoulder, right_shoulder, 
                               left_hip, right_hip, 
                               left_ankle, right_ankle):
        """
        Calculate hip position relative to the shoulder-ankle line.
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Hip position metric (-1 to 1, where 0 is aligned,
                  negative values indicate sagging, positive values indicate raising).
        """
        # Get midpoints
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, 
                        (left_shoulder[1] + right_shoulder[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, 
                  (left_hip[1] + right_hip[1]) / 2]
        ankle_mid = [(left_ankle[0] + right_ankle[0]) / 2, 
                    (left_ankle[1] + right_ankle[1]) / 2]
        
        # Calculate the line from ankles to shoulders
        ankle_to_shoulder = [shoulder_mid[0] - ankle_mid[0], 
                            shoulder_mid[1] - ankle_mid[1]]
        line_length = np.sqrt(ankle_to_shoulder[0]**2 + ankle_to_shoulder[1]**2)
        
        if line_length == 0:
            return 0  # Avoid division by zero
            
        normalized_line = [ankle_to_shoulder[0] / line_length, 
                         ankle_to_shoulder[1] / line_length]
        
        # Calculate the point on the line that's the same distance from the ankle
        # as the hip is (projected onto the line)
        ankle_to_hip = [hip_mid[0] - ankle_mid[0], hip_mid[1] - ankle_mid[1]]
        projection = (ankle_to_hip[0] * normalized_line[0] + 
                     ankle_to_hip[1] * normalized_line[1])
        
        point_on_line = [
            ankle_mid[0] + projection * normalized_line[0],
            ankle_mid[1] + projection * normalized_line[1]
        ]
        
        # Calculate perpendicular distance from hip to line
        hip_deviation = np.sqrt((hip_mid[0] - point_on_line[0])**2 + 
                              (hip_mid[1] - point_on_line[1])**2)
        
        # Determine sign (positive if hip is above line, negative if below)
        # This assumes y increases downward in the image
        perpendicular = [
            hip_mid[0] - point_on_line[0],
            hip_mid[1] - point_on_line[1]
        ]
        
        # Calculate the normal vector to the line (90 degrees counterclockwise)
        normal = [-normalized_line[1], normalized_line[0]]
        
        # Dot product determines which side the hip is on
        dot_product = perpendicular[0] * normal[0] + perpendicular[1] * normal[1]
        sign = 1 if dot_product >= 0 else -1
        
        # Normalize by body length to get a relative measure
        relative_deviation = (hip_deviation / line_length) * sign
        
        return relative_deviation
    
    def _calculate_body_alignment(self, left_ankle, right_ankle, 
                                 left_hip, right_hip, 
                                 left_shoulder, right_shoulder):
        """
        Calculate overall body alignment score.
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Alignment score (0-1, where 1 is perfect alignment).
        """
        # Get midpoints
        ankle_mid = [(left_ankle[0] + right_ankle[0]) / 2, 
                    (left_ankle[1] + right_ankle[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, 
                  (left_hip[1] + right_hip[1]) / 2]
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, 
                       (left_shoulder[1] + right_shoulder[1]) / 2]
        
        # Calculate the line from ankles to shoulders
        ankle_to_shoulder = [shoulder_mid[0] - ankle_mid[0], 
                           shoulder_mid[1] - ankle_mid[1]]
        line_length = np.sqrt(ankle_to_shoulder[0]**2 + ankle_to_shoulder[1]**2)
        
        if line_length == 0:
            return 1.0  # Avoid division by zero
            
        normalized_line = [ankle_to_shoulder[0] / line_length, 
                         ankle_to_shoulder[1] / line_length]
        
        # Calculate hip deviation from the line
        ankle_to_hip = [hip_mid[0] - ankle_mid[0], hip_mid[1] - ankle_mid[1]]
        
        # Project hip_to_ankle onto the line
        projection = (ankle_to_hip[0] * normalized_line[0] + 
                     ankle_to_hip[1] * normalized_line[1])
        
        # Calculate the point on the line
        point_on_line = [
            ankle_mid[0] + projection * normalized_line[0],
            ankle_mid[1] + projection * normalized_line[1]
        ]
        
        # Calculate perpendicular distance (hip deviation from line)
        hip_deviation = np.sqrt((hip_mid[0] - point_on_line[0])**2 + 
                              (hip_mid[1] - point_on_line[1])**2)
        
        # Normalize by body length and convert to a 0-1 score
        # where 1 means perfect alignment (0 deviation)
        alignment_score = 1.0 - min(1.0, (hip_deviation / line_length) * 5)
        return max(0.0, alignment_score)
    
    def _calculate_elbow_shoulder_alignment(self, left_shoulder, right_shoulder, 
                                          left_elbow, right_elbow):
        """
        Calculate alignment of elbows relative to shoulders.
        
        Args:
            Various upper body landmarks.
            
        Returns:
            float: Alignment score (0-1, where 1 is perfect alignment).
        """
        # Calculate horizontal offset for each arm
        left_offset = abs(left_elbow[0] - left_shoulder[0])
        right_offset = abs(right_elbow[0] - right_shoulder[0])
        
        # Calculate vertical distance
        left_vertical = abs(left_elbow[1] - left_shoulder[1])
        right_vertical = abs(right_elbow[1] - right_shoulder[1])
        
        # Normalize by vertical distance and convert to a 0-1 score
        # where 1 means perfect alignment (elbows directly under shoulders)
        if left_vertical == 0 or right_vertical == 0:
            return 0.5  # Default if can't calculate
        
        left_score = 1.0 - min(1.0, (left_offset / left_vertical) * 0.5)
        right_score = 1.0 - min(1.0, (right_offset / right_vertical) * 0.5)
        
        # Average the scores
        return (left_score + right_score) / 2
    
    def _calculate_head_alignment(self, nose, left_shoulder, right_shoulder, 
                                left_hip, right_hip):
        """
        Calculate head/neck alignment relative to the spine.
        
        Args:
            Various body landmarks.
            
        Returns:
            float: Head alignment deviation in degrees (0 is neutral,
                  positive values mean looking up, negative values mean looking down).
        """
        # Get midpoints
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, 
                       (left_shoulder[1] + right_shoulder[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, 
                  (left_hip[1] + right_hip[1]) / 2]
        
        # Calculate spine direction (hip to shoulder)
        spine_vector = [shoulder_mid[0] - hip_mid[0], 
                      shoulder_mid[1] - hip_mid[1]]
        spine_length = np.sqrt(spine_vector[0]**2 + spine_vector[1]**2)
        
        if spine_length == 0:
            return 0.0  # Avoid division by zero
            
        normalized_spine = [spine_vector[0] / spine_length, 
                          spine_vector[1] / spine_length]
        
        # Extend spine direction to estimate where head should be
        ideal_head_position = [
            shoulder_mid[0] + normalized_spine[0] * spine_length * 0.25,
            shoulder_mid[1] + normalized_spine[1] * spine_length * 0.25
        ]
        
        # Calculate the vector from shoulder to actual nose position
        actual_vector = [nose[0] - shoulder_mid[0], 
                       nose[1] - shoulder_mid[1]]
        
        # Calculate the vector from shoulder to ideal head position
        ideal_vector = [ideal_head_position[0] - shoulder_mid[0], 
                      ideal_head_position[1] - shoulder_mid[1]]
        
        # Calculate the angle between these vectors
        def angle_between(v1, v2):
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
            if mag1 * mag2 == 0:
                return 0.0  # Avoid division by zero
            cos_angle = dot / (mag1 * mag2)
            cos_angle = min(1.0, max(-1.0, cos_angle))  # Clamp to avoid numerical issues
            angle = np.arccos(cos_angle)
            return np.degrees(angle)
        
        # Get the angle
        angle = angle_between(actual_vector, ideal_vector)
        
        # Determine sign (positive if looking up, negative if looking down)
        # Use cross product to determine direction
        cross_z = actual_vector[0] * ideal_vector[1] - actual_vector[1] * ideal_vector[0]
        sign = 1 if cross_z >= 0 else -1
        
        return angle * sign
    
    def _update_stability_score(self, left_shoulder, right_shoulder, 
                              left_hip, right_hip):
        """
        Update stability score based on movement of reference points.
        
        Args:
            Various body landmarks used as reference points.
        """
        # Get midpoints
        shoulder_mid = [(left_shoulder[0] + right_shoulder[0]) / 2, 
                       (left_shoulder[1] + right_shoulder[1]) / 2]
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, 
                  (left_hip[1] + right_hip[1]) / 2]
        
        # Create a reference position from these points
        current_position = shoulder_mid + hip_mid
        
        # Add to history
        self.position_history.append(current_position)
        if len(self.position_history) > 10:
            self.position_history.pop(0)
        
        # Need at least 2 points to calculate movement
        if len(self.position_history) < 2:
            return
        
        # Calculate average movement between consecutive frames
        total_movement = 0
        for i in range(1, len(self.position_history)):
            prev = self.position_history[i-1]
            curr = self.position_history[i]
            
            # Calculate Euclidean distance for each point and sum
            shoulder_movement = np.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            hip_movement = np.sqrt((curr[2] - prev[2])**2 + (curr[3] - prev[3])**2)
            
            total_movement += shoulder_movement + hip_movement
        
        avg_movement = total_movement / (len(self.position_history) - 1)
        
        # Convert to a stability score (1.0 = perfectly stable, lower values = less stable)
        # Scale factor of 50 is chosen to make the score meaningful (adjust as needed)
        raw_stability = 1.0 - min(1.0, avg_movement * 50)
        
        # Smooth the stability score
        self.stability_score = 0.8 * self.stability_score + 0.2 * raw_stability
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """Get the comprehensive analysis result with exercise-specific state."""
        result = super().get_analysis_result()
        result['exercise_state'] = self.plank_state.name
        return result