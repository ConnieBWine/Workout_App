/**
 * Workout planning API service
 * 
 * This module provides functions to interact with the workout planning API endpoints,
 * including generating personalized workout plans and managing saved plans.
 */
import { get, post, del } from './api';

/**
 * Generate a personalized workout plan based on user profile
 * 
 * Uses AI to create a customized workout plan based on user parameters
 * 
 * @param {Object} params - Workout plan generation parameters
 * @param {Object} params.user_profile - User profile data
 * @param {number} params.user_profile.weight - User weight in kg
 * @param {number} params.user_profile.height - User height in cm
 * @param {string} params.user_profile.gender - User gender
 * @param {string} params.user_profile.activity - Activity level (e.g., 'sedentary', 'moderate', 'active')
 * @param {string} params.user_profile.goal - Fitness goal (e.g., 'strength', 'endurance', 'weight loss')
 * @param {string} params.user_profile.intensity - Desired workout intensity
 * @param {string} [params.additional_requirements] - Optional specific requirements or constraints
 * @returns {Promise<Object>} - Generated workout plan
 */
export const generateWorkoutPlan = (params) => {
  return post('workout/generate', params);
};

/**
 * Get all workout plans for the current user
 * 
 * Retrieves all saved workout plans for the logged-in user
 * 
 * @returns {Promise<Object>} - User's workout plans
 */
export const getWorkoutPlans = () => {
  return get('workout/plans');
};

/**
 * Get a specific workout plan by ID
 * 
 * Retrieves detailed information about a specific workout plan
 * 
 * @param {number} planId - ID of the workout plan to retrieve
 * @returns {Promise<Object>} - Detailed workout plan data
 */
export const getWorkoutPlan = (planId) => {
  return get(`workout/plans/${planId}`);
};

/**
 * Delete a specific workout plan
 * 
 * Permanently removes a workout plan from the user's saved plans
 * 
 * @param {number} planId - ID of the workout plan to delete
 * @returns {Promise<Object>} - Confirmation of deletion
 */
export const deleteWorkoutPlan = (planId) => {
  return del(`workout/plans/${planId}`);
};

/**
 * Start a workout session for a specific plan
 * 
 * Begins a workout session tracking for the specified plan
 * 
 * @param {number} planId - ID of the workout plan to start
 * @returns {Promise<Object>} - Workout plan with session information
 */
export const startWorkoutPlan = (planId) => {
  return post(`workout/plans/${planId}/start`, {});
};

/**
 * Get the currently active workout plan in session
 * 
 * Retrieves the workout plan currently in progress
 * 
 * @returns {Promise<Object>} - Current workout plan
 */
export const getCurrentWorkout = () => {
  return get('workout/current');
};

/**
 * Create an exercise sequence for a day in a workout plan
 * 
 * Converts a workout day into a sequential list of exercises for execution
 * 
 * @param {Object} workoutDay - Day object from a workout plan
 * @returns {Array} - Sequenced list of exercises with metadata
 */
export const createExerciseSequence = (workoutDay) => {
  if (!workoutDay || !workoutDay.exercises || !Array.isArray(workoutDay.exercises)) {
    return [];
  }
  
  return workoutDay.exercises.map(exercise => ({
    id: exercise.name.toLowerCase().replace(/\s+/g, '_'),
    name: exercise.name,
    sets: exercise.sets || 1,
    reps: exercise.reps || 10,
    is_timed: exercise.is_timed || false,
    target_duration: exercise.is_timed ? exercise.reps : null,
    target_reps: !exercise.is_timed ? exercise.reps : null,
    completed: false
  }));
};

export default {
  generateWorkoutPlan,
  getWorkoutPlans,
  getWorkoutPlan,
  deleteWorkoutPlan,
  startWorkoutPlan,
  getCurrentWorkout,
  createExerciseSequence
};