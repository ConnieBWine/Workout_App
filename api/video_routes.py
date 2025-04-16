"""
Video streaming API routes for workout tracking application.

This module defines the API endpoints for video streaming functionality,
providing real-time video feed with pose detection and exercise analysis.
"""
from flask import Blueprint, Response, request, jsonify, session
import cv2
import numpy as np
import threading
import time
import base64
from typing import Dict, Any, Optional

# Create Blueprint for video routes
video_bp = Blueprint('video', __name__, url_prefix='/api/video')

# Global video processor instance (to be set by the main application)
video_processor = None
camera = None
camera_lock = threading.Lock()

# Video frame buffer for when using webcam
frame_buffer = None
frame_buffer_lock = threading.Lock()
frame_buffer_updated = threading.Event()

# Flag to control the background frame processing thread
processing_active = False
processing_thread = None


def initialize_camera(camera_index=0):
    """
    Initialize the camera for video capture.
    
    Args:
        camera_index: Index of the camera to use.
        
    Returns:
        True if camera was initialized successfully, False otherwise.
    """
    global camera
    
    with camera_lock:
        # Release existing camera if any
        if camera is not None:
            camera.release()
        
        # Initialize new camera
        camera = cv2.VideoCapture(camera_index)
        
        # Set camera properties
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        
        return camera.isOpened()


def release_camera():
    """Release the camera resource."""
    global camera
    
    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None


def start_frame_processing():
    """Start the background frame processing thread."""
    global processing_active, processing_thread
    
    if processing_thread is not None and processing_thread.is_alive():
        # Thread already running
        return
    
    processing_active = True
    processing_thread = threading.Thread(target=process_frames_loop)
    processing_thread.daemon = True
    processing_thread.start()


def stop_frame_processing():
    """Stop the background frame processing thread."""
    global processing_active
    
    processing_active = False
    if processing_thread is not None:
        if processing_thread.is_alive():
            processing_thread.join(timeout=1.0)


def process_frames_loop():
    """Background thread that continuously processes frames from the camera."""
    global frame_buffer, processing_active, video_processor, camera
    
    while processing_active:
        with camera_lock:
            if camera is None or not camera.isOpened():
                time.sleep(0.1)
                continue
            
            success, frame = camera.read()
        
        if not success:
            time.sleep(0.1)
            continue
        
        # Process frame with video processor
        if video_processor is not None:
            processed_frame, _ = video_processor.process_frame(frame)
        else:
            processed_frame = frame
        
        # Update frame buffer
        with frame_buffer_lock:
            frame_buffer = processed_frame.copy()
        
        # Signal that frame buffer has been updated
        frame_buffer_updated.set()
        
        # Small sleep to avoid consuming too much CPU
        time.sleep(0.01)


def generate_frames():
    """
    Generator function to yield processed video frames for streaming.
    
    Yields:
        JPEG-encoded frames for multipart HTTP response.
    """
    global frame_buffer, frame_buffer_updated
    
    while True:
        # Wait for new frame with timeout
        if not frame_buffer_updated.wait(timeout=0.5):
            # If no frame received within timeout, yield a blank frame
            blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', blank_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            continue
        
        # Reset event for next iteration
        frame_buffer_updated.clear()
        
        # Get current frame from buffer
        with frame_buffer_lock:
            if frame_buffer is None:
                continue
            current_frame = frame_buffer.copy()
        
        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', current_frame)
        frame_bytes = buffer.tobytes()
        
        # Yield frame for HTTP response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@video_bp.route('/feed')
def video_feed():
    """
    Stream the processed video feed.
    
    Returns:
        Multipart HTTP response with JPEG frames.
    """
    global processing_active
    
    # Ensure camera and processing are initialized
    if not processing_active:
        initialize_camera()
        start_frame_processing()
    
    # Return streaming response
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@video_bp.route('/frame', methods=['GET'])
def get_current_frame():
    """
    Get the current processed frame as a base64-encoded JPEG.
    
    Returns:
        JSON response with base64-encoded frame.
    """
    global frame_buffer
    
    with frame_buffer_lock:
        if frame_buffer is None:
            return jsonify({
                'success': False,
                'error': 'No frame available'
            }), 404
        
        current_frame = frame_buffer.copy()
    
    # Encode frame to JPEG and then to base64
    _, buffer = cv2.imencode('.jpg', current_frame)
    b64_frame = base64.b64encode(buffer).decode('utf-8')
    
    return jsonify({
        'success': True,
        'frame': b64_frame,
        'width': current_frame.shape[1],
        'height': current_frame.shape[0],
        'timestamp': time.time()
    })


@video_bp.route('/start', methods=['POST'])
def start_video():
    """
    Start video processing.
    
    Request JSON:
        {
            "camera_index": 0  // Optional, default is 0
        }
        
    Returns:
        JSON response indicating success or failure.
    """
    camera_index = request.json.get('camera_index', 0) if request.is_json else 0
    
    success = initialize_camera(camera_index)
    if not success:
        return jsonify({
            'success': False,
            'error': f'Failed to initialize camera at index {camera_index}'
        }), 500
    
    start_frame_processing()
    
    return jsonify({
        'success': True,
        'message': 'Video processing started'
    })


@video_bp.route('/stop', methods=['POST'])
def stop_video():
    """
    Stop video processing and release camera.
    
    Returns:
        JSON response indicating success.
    """
    stop_frame_processing()
    release_camera()
    
    return jsonify({
        'success': True,
        'message': 'Video processing stopped'
    })


@video_bp.route('/status', methods=['GET'])
def get_video_status():
    """
    Get current status of video processing.
    
    Returns:
        JSON response with video processing status.
    """
    global camera, processing_active
    
    camera_initialized = False
    with camera_lock:
        camera_initialized = camera is not None and camera.isOpened()
    
    return jsonify({
        'camera_initialized': camera_initialized,
        'processing_active': processing_active,
        'frame_available': frame_buffer is not None
    })