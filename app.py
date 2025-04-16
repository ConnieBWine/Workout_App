"""
Main Flask application for workout tracking and analysis system.

This module initializes and configures the Flask application,
registers all blueprints, sets up database connections,
and provides the entry point for running the application.
"""
import os
import logging
from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from flask_cors import CORS
import google.generativeai as genai

# Import configuration
from config import (
    SECRET_KEY, DEBUG, DATABASE_URI, 
    GOOGLE_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT
)

# Import database models
from database.models import db, User

# Import API blueprints
from api.exercise_routes import exercise_bp, video_processor
from api.video_routes import video_bp
from api.workout_routes import workout_bp

# Import video processing module
from modules.video_processor import VideoProcessor
from api.video_routes import initialize_camera, start_frame_processing, stop_frame_processing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Configured Flask application instance.
    """
    # Initialize Flask app
    app = Flask(__name__, 
                static_folder='./static/build/static', 
                template_folder='./static/build')
    
    # Configure app
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development
    
    # Enable CORS
    CORS(app)
    
    # Initialize database
    db.init_app(app)
    
    # Configure Google Generative AI
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Register blueprints
    app.register_blueprint(exercise_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(workout_bp)
    
    # Initialize database tables
    with app.app_context():
        db.create_all()
    
    # Share video processor instance with routes
    global video_processor
    video_processor = VideoProcessor()
    
    # Update video processor reference in routes
    from api.video_routes import video_processor as video_route_processor
    video_route_processor = video_processor
    
    from api.exercise_routes import video_processor as exercise_route_processor
    exercise_route_processor = video_processor
    
    # Define routes
    @app.route('/')
    def index():
        """Serve the React frontend."""
        return render_template('index.html')
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0'
        })
    
    @app.route('/api/user/profile', methods=['GET', 'POST'])
    def user_profile():
        """Get or update user profile data."""
        if request.method == 'GET':
            # Get user profile data from session
            user_profile = session.get('user_profile', {})
            return jsonify(user_profile)
        else:
            # Update user profile data
            profile_data = request.json
            session['user_profile'] = profile_data
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
    
    @app.route('/api/session/clear', methods=['POST'])
    def clear_session():
        """Clear the session data."""
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Session cleared'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors by serving React frontend."""
        return render_template('index.html')
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500
    
    # Cleanup resources on application shutdown
    @app.teardown_appcontext
    def cleanup_resources(exception=None):
        """Clean up resources when the application shuts down."""
        stop_frame_processing()
    
    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    
    # Initialize camera and start frame processing
    initialize_camera()
    start_frame_processing()
    
    try:
        # Run the Flask application
        app.run(host='0.0.0.0', port=port, debug=DEBUG, threaded=True)
    finally:
        # Ensure cleanup on exit
        stop_frame_processing()