"""
Mediapipe-based pose detection module.
Handles the detection and processing of human pose landmarks.
"""
import cv2
import mediapipe as mp
import numpy as np
from config import (
    POSE_DETECTION_MIN_DETECTION_CONFIDENCE,
    POSE_DETECTION_MIN_TRACKING_CONFIDENCE,
    POSE_DETECTION_MODEL_COMPLEXITY
)

class PoseDetector:
    """
    A class for detecting human pose landmarks using MediaPipe.
    
    This class encapsulates the MediaPipe pose detection functionality,
    providing methods to find pose landmarks and draw them on images.
    """
    
    def __init__(self):
        """Initialize the pose detector with MediaPipe components."""
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=POSE_DETECTION_MODEL_COMPLEXITY,
            smooth_landmarks=True,
            min_detection_confidence=POSE_DETECTION_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=POSE_DETECTION_MIN_TRACKING_CONFIDENCE
        )
        
        # Drawing specifications for visualization
        self.landmark_drawing_spec = self.mp_drawing.DrawingSpec(
            color=(0, 255, 0), 
            thickness=2, 
            circle_radius=2
        )
        self.connection_drawing_spec = self.mp_drawing.DrawingSpec(
            color=(255, 0, 0), 
            thickness=2, 
            circle_radius=2
        )

    def find_pose(self, image):
        """
        Process an image to find pose landmarks.
        
        Args:
            image: Input image (BGR format from OpenCV).
            
        Returns:
            MediaPipe pose processing results.
        """
        # Convert BGR image to RGB for MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Process the image to find poses
        results = self.pose.process(image_rgb)
        
        return results

    def draw_landmarks(self, image, results):
        """
        Draw detected pose landmarks on the image.
        
        Args:
            image: Input image to draw on.
            results: MediaPipe pose processing results.
            
        Returns:
            Image with landmarks drawn on it.
        """
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS,
                self.landmark_drawing_spec,
                self.connection_drawing_spec
            )
        
        return image

    def extract_landmarks(self, results, image_shape):
        """
        Extract normalized and pixel coordinates of pose landmarks.
        
        Args:
            results: MediaPipe pose processing results.
            image_shape: Shape of the image (height, width).
            
        Returns:
            Dictionary of landmark positions with normalized and pixel coordinates.
        """
        landmarks = {}
        
        if not results.pose_landmarks:
            return landmarks
        
        h, w = image_shape[:2]
        
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            # Store both normalized coordinates (0-1) and pixel coordinates
            landmarks[idx] = {
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility,
                'px': int(landmark.x * w),
                'py': int(landmark.y * h)
            }
        
        return landmarks

    def get_pose_visibility(self, results, threshold=0.5):
        """
        Calculate overall pose visibility score.
        
        Args:
            results: MediaPipe pose processing results.
            threshold: Minimum visibility threshold.
            
        Returns:
            Tuple of (visibility_score, is_visible).
        """
        if not results.pose_landmarks:
            return 0.0, False
        
        # Calculate average visibility of key landmarks
        key_landmarks = [
            self.mp_pose.PoseLandmark.LEFT_SHOULDER,
            self.mp_pose.PoseLandmark.RIGHT_SHOULDER,
            self.mp_pose.PoseLandmark.LEFT_HIP,
            self.mp_pose.PoseLandmark.RIGHT_HIP,
            self.mp_pose.PoseLandmark.LEFT_KNEE,
            self.mp_pose.PoseLandmark.RIGHT_KNEE,
            self.mp_pose.PoseLandmark.LEFT_ANKLE,
            self.mp_pose.PoseLandmark.RIGHT_ANKLE,
        ]
        
        visibility_sum = sum(
            results.pose_landmarks.landmark[lm.value].visibility 
            for lm in key_landmarks
        )
        visibility_score = visibility_sum / len(key_landmarks)
        
        return visibility_score, visibility_score >= threshold