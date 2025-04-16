"""
Angle calculator module for exercise pose analysis.

This module provides a class for calculating various angles between body landmarks,
which is essential for analyzing exercise form and posture.
"""
import numpy as np
import math

class AngleCalculator:
    """
    A utility class for calculating angles between body landmarks.
    
    Provides various methods to calculate angles between points, which represent
    body landmarks detected by the pose detector.
    """
    
    @staticmethod
    def calculate_angle(a, b, c):
        """
        Calculate the angle between three points (a-b-c).
        
        Args:
            a (list or tuple): Coordinates of first point.
            b (list or tuple): Coordinates of second point (vertex).
            c (list or tuple): Coordinates of third point.
            
        Returns:
            float: Angle in degrees.
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        # Calculate vectors
        ba = a - b
        bc = c - b
        
        # Calculate the angle using dot product
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        # Clip to handle potential numerical errors
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.arccos(cosine_angle)
        
        # Convert to degrees
        angle = np.degrees(angle)
        
        return angle

    @staticmethod
    def calculate_angle_2d(a, b, c):
        """
        Calculate the 2D angle between three points (a-b-c).
        
        Args:
            a (list or tuple): Coordinates of first point [x, y].
            b (list or tuple): Coordinates of second point (vertex) [x, y].
            c (list or tuple): Coordinates of third point [x, y].
            
        Returns:
            float: Angle in degrees.
        """
        # Extract 2D coordinates if more are provided
        if len(a) > 2:
            a = a[:2]
        if len(b) > 2:
            b = b[:2]
        if len(c) > 2:
            c = c[:2]
            
        return AngleCalculator.calculate_angle(a, b, c)

    @staticmethod
    def angle_deg(p1, pref, p2):
        """
        Calculate the angle between three points where pref is the reference point.
        
        Args:
            p1 (list or tuple): Coordinates of first point.
            pref (list or tuple): Coordinates of reference point.
            p2 (list or tuple): Coordinates of second point.
            
        Returns:
            float: Angle in degrees.
        """
        # Ensure we're working with numpy arrays
        p1 = np.array(p1[:2])
        pref = np.array(pref[:2])
        p2 = np.array(p2[:2])
        
        # Calculate vectors from reference point
        p1ref = p1 - pref
        p2ref = p2 - pref
        
        # Calculate dot product
        dot_product = np.dot(p1ref, p2ref)
        
        # Calculate magnitudes
        magnitude_p1ref = np.linalg.norm(p1ref)
        magnitude_p2ref = np.linalg.norm(p2ref)
        
        # Calculate cosine of angle
        if magnitude_p1ref == 0 or magnitude_p2ref == 0:
            return 0.0
            
        cos_theta = dot_product / (magnitude_p1ref * magnitude_p2ref)
        
        # Ensure cos_theta is in valid range [-1, 1] to prevent numerical errors
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        
        # Calculate angle in radians and convert to degrees
        angle_rad = np.arccos(cos_theta)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg

    @staticmethod
    def calculate_vertical_angle(point1, point2):
        """
        Calculate the angle between a line and the vertical axis.
        
        Args:
            point1 (list or tuple): Coordinates of first point [x, y].
            point2 (list or tuple): Coordinates of second point [x, y].
            
        Returns:
            float: Angle in degrees.
        """
        x1, y1 = point1[:2]
        x2, y2 = point2[:2]
        
        dx = x2 - x1
        dy = y2 - y1
        
        # Calculate angle with vertical axis (negative y-axis)
        angle = np.abs(np.arctan2(dx, -dy) * 180.0 / np.pi)
        
        return angle

    @staticmethod
    def calculate_horizontal_angle(point1, point2):
        """
        Calculate the angle between a line and the horizontal axis.
        
        Args:
            point1 (list or tuple): Coordinates of first point [x, y].
            point2 (list or tuple): Coordinates of second point [x, y].
            
        Returns:
            float: Angle in degrees.
        """
        x1, y1 = point1[:2]
        x2, y2 = point2[:2]
        
        dx = x2 - x1
        dy = y2 - y1
        
        # Calculate angle with horizontal axis (positive x-axis)
        angle = np.abs(np.arctan2(dy, dx) * 180.0 / np.pi)
        
        return angle

    @staticmethod
    def find_distance(point1, point2):
        """
        Calculate the Euclidean distance between two points.
        
        Args:
            point1 (list or tuple): Coordinates of first point.
            point2 (list or tuple): Coordinates of second point.
            
        Returns:
            float: Distance between the points.
        """
        if isinstance(point1, (list, tuple)) and len(point1) >= 2:
            x1, y1 = point1[:2]
        else:
            x1, y1 = point1, point1
            
        if isinstance(point2, (list, tuple)) and len(point2) >= 2:
            x2, y2 = point2[:2]
        else:
            x2, y2 = point2, point2
        
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return dist

    @staticmethod
    def calculate_body_alignment(left_landmark, right_landmark):
        """
        Calculate body alignment based on corresponding left and right landmarks.
        
        Args:
            left_landmark (list or tuple): Coordinates of left body point.
            right_landmark (list or tuple): Coordinates of right body point.
            
        Returns:
            float: Alignment score (0 to 1, where 1 is perfect alignment).
        """
        # Calculate vertical alignment (y-coordinates should be similar)
        y_diff = abs(left_landmark[1] - right_landmark[1])
        
        # Normalize by the distance between points
        distance = AngleCalculator.find_distance(left_landmark, right_landmark)
        
        if distance == 0:
            return 1.0  # Avoid division by zero
            
        alignment_score = 1.0 - (y_diff / distance)
        return max(0.0, min(1.0, alignment_score))  # Clip to range [0, 1]

    @staticmethod
    def calculate_elbow_torso_angle(left_hip, left_shoulder, left_elbow, 
                                    right_hip, right_shoulder, right_elbow, 
                                    visibility_threshold=0.6):
        """
        Calculate the angle between elbow and torso for both left and right sides.
        
        Args:
            left_hip, left_shoulder, left_elbow: Left side landmarks with visibility.
            right_hip, right_shoulder, right_elbow: Right side landmarks with visibility.
            visibility_threshold: Minimum visibility score to consider landmarks.
            
        Returns:
            tuple: (left_angle, right_angle, avg_angle, view_position)
        """
        def is_visible(points):
            """Check if all points are visible based on threshold."""
            return all(point[2] > visibility_threshold for point in points)

        left_visible = is_visible([left_hip, left_shoulder, left_elbow])
        right_visible = is_visible([right_hip, right_shoulder, right_elbow])

        if left_visible and right_visible:
            left_angle = AngleCalculator.angle_deg(left_hip, left_shoulder, left_elbow)
            right_angle = AngleCalculator.angle_deg(right_hip, right_shoulder, right_elbow)
            return left_angle, right_angle, (left_angle + right_angle) / 2, "front"
        elif left_visible:
            left_angle = AngleCalculator.angle_deg(left_hip, left_shoulder, left_elbow)
            return left_angle, None, left_angle, "left_side"
        elif right_visible:
            right_angle = AngleCalculator.angle_deg(right_hip, right_shoulder, right_elbow)
            return None, right_angle, right_angle, "right_side"
        else:
            return None, None, None, "unclear"
            
    @staticmethod
    def calculate_hip_shoulder_angle(hip, shoulder, visibility_threshold=0.6):
        """
        Calculate the angle between hip and shoulder relative to vertical.
        
        Args:
            hip: Hip landmark with visibility.
            shoulder: Shoulder landmark with visibility.
            visibility_threshold: Minimum visibility score to consider landmarks.
            
        Returns:
            float or None: Angle in degrees or None if not visible.
        """
        if hip[2] > visibility_threshold and shoulder[2] > visibility_threshold:
            return AngleCalculator.calculate_vertical_angle(hip[:2], shoulder[:2])
        else:
            return None