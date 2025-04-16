/**
 * Exercise tracking API service
 * 
 * This module provides functions to interact with the exercise tracking API endpoints,
 * including starting/stopping exercises and retrieving exercise data.
 */
import { get, post } from './api';

/**
 * Start tracking a specific exercise
 * 
 * Initiates exercise tracking session with specified parameters
 * 
 * @param {Object} params - Exercise configuration parameters
 * @param {string} params.exercise - Exercise ID/name (e.g., 'bicep_curl', 'squat')
 * @param {boolean} params.is_timed - Whether this is a timed exercise 
 * @param {number} [params.target_reps] - Target number of repetitions (for rep-based exercises)
 * @param {number} [params.target_duration] - Target duration in seconds (for timed exercises)
 * @returns {Promise<Object>} - API response with start confirmation
 */
export const startExercise = (params) => {
  return post('exercise/start', params);
};

/**
 * Stop the currently active exercise tracking session
 * 
 * Ends the current exercise tracking session and returns summary statistics
 * 
 * @returns {Promise<Object>} - API response with exercise statistics
 */
export const stopExercise = () => {
  return post('exercise/stop', {});
};

/**
 * Get current exercise tracking data
 * 
 * Retrieves the latest data for the currently active exercise, including:
 * - Rep count or elapsed time
 * - Exercise state
 * - Form feedback
 * - Detailed metrics
 * 
 * @returns {Promise<Object>} - Current exercise tracking data
 */
export const getExerciseData = () => {
  return get('exercise/data');
};

/**
 * Get exercise statistics for the current session
 * 
 * Retrieves comprehensive statistics about the current exercise session
 * 
 * @returns {Promise<Object>} - Exercise session statistics
 */
export const getExerciseStats = () => {
  return get('exercise/stats');
};

/**
 * Get historical exercise data
 * 
 * Retrieves exercise history for the currently logged-in user
 * 
 * @returns {Promise<Object>} - Exercise history data
 */
export const getExerciseHistory = () => {
  return get('exercise/history');
};

/**
 * Get common feedback for exercises
 * 
 * Retrieves aggregated feedback statistics, optionally filtered by exercise and time period
 * 
 * @param {Object} [params] - Query parameters
 * @param {string} [params.exercise] - Optional exercise filter
 * @param {string} [params.period='month'] - Time period ('session', 'week', 'month')
 * @returns {Promise<Object>} - Common feedback data
 */
export const getCommonFeedback = (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.exercise) {
    queryParams.append('exercise', params.exercise);
  }
  
  if (params.period) {
    queryParams.append('period', params.period);
  }
  
  const queryString = queryParams.toString();
  return get(`exercise/common_feedback${queryString ? `?${queryString}` : ''}`);
};

export default {
  startExercise,
  stopExercise,
  getExerciseData,
  getExerciseStats,
  getExerciseHistory,
  getCommonFeedback
};