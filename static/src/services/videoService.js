/**
 * Video processing API service
 * 
 * This module provides functions to interact with the video processing API endpoints,
 * controlling video feed initialization, frame processing, and camera resources.
 */
import { get, post } from './api';

/**
 * Start the video processing feed
 * 
 * Initializes the camera and starts the background video processing
 * 
 * @param {Object} params - Video initialization parameters
 * @param {number} [params.camera_index=0] - Index of the camera to use (0 = default)
 * @returns {Promise<Object>} - API response with initialization status
 */
export const startVideoFeed = (params = { camera_index: 0 }) => {
  return post('video/start', params);
};

/**
 * Stop the video processing feed
 * 
 * Stops background processing and releases camera resources
 * 
 * @returns {Promise<Object>} - API response with status
 */
export const stopVideoFeed = () => {
  return post('video/stop', {});
};

/**
 * Get the current video processing status
 * 
 * Retrieves information about the current state of video processing
 * 
 * @returns {Promise<Object>} - Video processing status information
 */
export const getVideoStatus = () => {
  return get('video/status');
};

/**
 * Get the current processed frame as base64 image
 * 
 * Retrieves the latest processed video frame as a base64-encoded JPEG
 * 
 * @returns {Promise<Object>} - Object containing frame data and metadata
 */
export const getCurrentFrame = () => {
  return get('video/frame');
};

/**
 * Get the direct URL for the video feed stream
 * 
 * Returns the URL for the MJPEG stream that can be used as an image source
 * 
 * @returns {string} - URL for the video feed
 */
export const getVideoFeedUrl = () => {
  return `/api/video/feed`;
};

/**
 * Helper function to check if the browser supports camera access
 * 
 * @returns {Promise<boolean>} - Promise resolving to true if camera access is supported
 */
export const checkCameraSupport = async () => {
  try {
    // Check if the browser supports getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return false;
    }
    
    // Request camera access to check permissions
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    
    // Release the camera immediately
    stream.getTracks().forEach(track => track.stop());
    
    return true;
  } catch (error) {
    console.error('Camera access check failed:', error);
    return false;
  }
};

export default {
  startVideoFeed,
  stopVideoFeed,
  getVideoStatus,
  getCurrentFrame,
  getVideoFeedUrl,
  checkCameraSupport
};