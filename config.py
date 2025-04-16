"""
Configuration settings for the workout application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'workout_app_secret_key')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Database configuration
DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///workout_app.db')

# Exercise detection thresholds
THRESHOLDS = {
    # Squat thresholds
    'squat_too_deep': 68,
    'squat_not_deep_enough': 91,
    'squat_forward_bend_too_little': 19,
    'squat_forward_bend_too_much': 50,
    
    # Bicep curl thresholds
    'bicep_curl_not_low_enough': 160,
    'bicep_curl_not_high_enough': 90,
    'bicep_curl_elbow_movement': 5,
    'bicep_curl_body_swing': 10,
    
    # Pushup thresholds
    'pushup_not_low_enough': 100,
    'pushup_elbow_flare': 30,
    'pushup_hip_sag': 30,
    'pushup_neck_alignment': 20,
    
    # Lunge thresholds
    'lunge_knee_angle_front': 100,
    'lunge_knee_angle_back': 120,
    'lunge_torso_angle': 20,
    
    # Plank thresholds
    'plank_hip_sag': 160,
    'plank_hip_pike': 200,
    'plank_head_alignment': 15,
    
    # Shoulder press thresholds
    'shoulder_press_elbow_angle': 160,
    'shoulder_press_wrist_alignment': 15,
    'shoulder_press_back_arch': 20,
    
    # Jumping jack thresholds
    'jumping_jack_arm_extension': 150,
    'jumping_jack_leg_spread': 30
}

# MediaPipe pose detection settings
POSE_DETECTION_MIN_DETECTION_CONFIDENCE = 0.6
POSE_DETECTION_MIN_TRACKING_CONFIDENCE = 0.6
POSE_DETECTION_MODEL_COMPLEXITY = 1

# Video processing settings
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30

# API Keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyAnDOY0QfkgyucCZ8r323YiQ1ZULqGGWwc')