import React, { createContext, useContext, useState, useReducer, useEffect } from 'react';
import { getCurrentWorkout } from '../services/workoutService';

/**
 * Workout State Management Context
 * 
 * This module provides global state management for workout-related data,
 * including active workouts, exercise progression, and session history.
 * It uses React Context API with a reducer pattern for predictable state updates.
 */

// Define initial workout state
const initialState = {
  // Current workout plan
  currentWorkout: null,
  
  // Current exercise sequence (flattened list of exercises to perform)
  exerciseSequence: [],
  
  // Current position in the exercise sequence
  currentExerciseIndex: -1,
  
  // Active exercise data
  activeExercise: null,
  
  // Session tracking
  sessionStartTime: null,
  sessionStats: {
    completedExercises: 0,
    totalReps: 0,
    totalDuration: 0,
    feedback: {}
  },
  
  // UI state
  isLoading: false,
  error: null
};

// Action types for the reducer
const ActionTypes = {
  SET_CURRENT_WORKOUT: 'SET_CURRENT_WORKOUT',
  SET_EXERCISE_SEQUENCE: 'SET_EXERCISE_SEQUENCE',
  SET_CURRENT_EXERCISE: 'SET_CURRENT_EXERCISE',
  COMPLETE_EXERCISE: 'COMPLETE_EXERCISE',
  START_SESSION: 'START_SESSION',
  END_SESSION: 'END_SESSION',
  UPDATE_SESSION_STATS: 'UPDATE_SESSION_STATS',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  RESET_STATE: 'RESET_STATE'
};

/**
 * Workout state reducer function
 * 
 * Handles all state transitions in a predictable, immutable manner
 * 
 * @param {Object} state - Current workout state
 * @param {Object} action - Action object with type and payload
 * @returns {Object} New workout state
 */
const workoutReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_CURRENT_WORKOUT:
      return {
        ...state,
        currentWorkout: action.payload,
        error: null
      };
      
    case ActionTypes.SET_EXERCISE_SEQUENCE:
      return {
        ...state,
        exerciseSequence: action.payload,
        currentExerciseIndex: -1,
        activeExercise: null
      };
      
    case ActionTypes.SET_CURRENT_EXERCISE:
      return {
        ...state,
        currentExerciseIndex: action.payload,
        activeExercise: state.exerciseSequence[action.payload] || null
      };
      
    case ActionTypes.COMPLETE_EXERCISE:
      const { exerciseIndex, stats } = action.payload;
      const updatedSequence = [...state.exerciseSequence];
      
      if (updatedSequence[exerciseIndex]) {
        updatedSequence[exerciseIndex] = {
          ...updatedSequence[exerciseIndex],
          completed: true,
          results: stats
        };
      }
      
      return {
        ...state,
        exerciseSequence: updatedSequence,
        sessionStats: {
          ...state.sessionStats,
          completedExercises: state.sessionStats.completedExercises + 1,
          totalReps: state.sessionStats.totalReps + (stats.repCount || 0),
          totalDuration: state.sessionStats.totalDuration + (stats.duration || 0)
        }
      };
      
    case ActionTypes.START_SESSION:
      return {
        ...state,
        sessionStartTime: new Date().toISOString(),
        sessionStats: {
          completedExercises: 0,
          totalReps: 0,
          totalDuration: 0,
          feedback: {}
        }
      };
      
    case ActionTypes.END_SESSION:
      return {
        ...state,
        activeExercise: null,
        sessionStats: {
          ...state.sessionStats,
          endTime: new Date().toISOString(),
          summary: action.payload
        }
      };
      
    case ActionTypes.UPDATE_SESSION_STATS:
      return {
        ...state,
        sessionStats: {
          ...state.sessionStats,
          ...action.payload
        }
      };
      
    case ActionTypes.SET_LOADING:
      return {
        ...state,
        isLoading: action.payload
      };
      
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        isLoading: false
      };
      
    case ActionTypes.RESET_STATE:
      return initialState;
      
    default:
      return state;
  }
};

// Create the workout context
const WorkoutContext = createContext();

/**
 * Workout Provider Component
 * 
 * Provides workout state and actions to all child components
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 */
export const WorkoutProvider = ({ children }) => {
  // Initialize state with reducer
  const [state, dispatch] = useReducer(workoutReducer, initialState);
  
  // Local UI state for modals and transitions
  const [showExerciseModal, setShowExerciseModal] = useState(false);
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  
  // Load current workout from session if available
  useEffect(() => {
    const loadCurrentWorkout = async () => {
      try {
        dispatch({ type: ActionTypes.SET_LOADING, payload: true });
        const response = await getCurrentWorkout();
        
        if (response && response.success && response.workout_plan) {
          dispatch({ 
            type: ActionTypes.SET_CURRENT_WORKOUT, 
            payload: response.workout_plan 
          });
        }
      } catch (error) {
        console.error('Failed to load current workout:', error);
        // Don't set error state here to avoid showing error on initial load
      } finally {
        dispatch({ type: ActionTypes.SET_LOADING, payload: false });
      }
    };
    
    loadCurrentWorkout();
  }, []);
  
  /**
   * Sets the current workout plan
   * 
   * @param {Object} workout - Workout plan data
   */
  const setCurrentWorkout = (workout) => {
    dispatch({ type: ActionTypes.SET_CURRENT_WORKOUT, payload: workout });
  };
  
  /**
   * Sets the exercise sequence for the current workout
   * 
   * @param {Array} sequence - Array of exercise objects
   */
  const setExerciseSequence = (sequence) => {
    dispatch({ type: ActionTypes.SET_EXERCISE_SEQUENCE, payload: sequence });
  };
  
  /**
   * Sets the current exercise by index
   * 
   * @param {number} index - Index of current exercise in sequence
   */
  const setCurrentExercise = (index) => {
    dispatch({ type: ActionTypes.SET_CURRENT_EXERCISE, payload: index });
    
    // If jumping to a valid exercise, show the exercise modal
    if (index >= 0 && index < state.exerciseSequence.length) {
      setShowExerciseModal(true);
    } else {
      setShowExerciseModal(false);
    }
  };
  
  /**
   * Marks the current exercise as completed with statistics
   * 
   * @param {Object} stats - Exercise completion statistics
   */
  const completeCurrentExercise = (stats) => {
    if (state.currentExerciseIndex >= 0) {
      dispatch({ 
        type: ActionTypes.COMPLETE_EXERCISE, 
        payload: { 
          exerciseIndex: state.currentExerciseIndex, 
          stats 
        } 
      });
    }
  };
  
  /**
   * Starts a new workout session
   */
  const startWorkoutSession = () => {
    dispatch({ type: ActionTypes.START_SESSION });
  };
  
  /**
   * Ends the current workout session with summary
   * 
   * @param {Object} summary - Session summary data
   */
  const endWorkoutSession = (summary) => {
    dispatch({ type: ActionTypes.END_SESSION, payload: summary });
    setShowSummaryModal(true);
  };
  
  /**
   * Updates session statistics with new data
   * 
   * @param {Object} stats - Updated session statistics
   */
  const updateSessionStats = (stats) => {
    dispatch({ type: ActionTypes.UPDATE_SESSION_STATS, payload: stats });
  };
  
  /**
   * Advances to the next exercise in sequence
   */
  const goToNextExercise = () => {
    const nextIndex = state.currentExerciseIndex + 1;
    if (nextIndex < state.exerciseSequence.length) {
      setCurrentExercise(nextIndex);
    } else {
      // End of sequence
      setShowExerciseModal(false);
      setShowSummaryModal(true);
    }
  };
  
  /**
   * Goes back to the previous exercise in sequence
   */
  const goToPreviousExercise = () => {
    const prevIndex = state.currentExerciseIndex - 1;
    if (prevIndex >= 0) {
      setCurrentExercise(prevIndex);
    }
  };
  
  /**
   * Resets the workout state completely
   */
  const resetWorkoutState = () => {
    dispatch({ type: ActionTypes.RESET_STATE });
    setShowExerciseModal(false);
    setShowSummaryModal(false);
  };
  
  // Construct the context value object
  const contextValue = {
    // State
    currentWorkout: state.currentWorkout,
    exerciseSequence: state.exerciseSequence,
    currentExerciseIndex: state.currentExerciseIndex,
    activeExercise: state.activeExercise,
    sessionStats: state.sessionStats,
    isLoading: state.isLoading,
    error: state.error,
    showExerciseModal,
    showSummaryModal,
    
    // Actions
    setCurrentWorkout,
    setExerciseSequence,
    setCurrentExercise,
    completeCurrentExercise,
    startWorkoutSession,
    endWorkoutSession,
    updateSessionStats,
    goToNextExercise,
    goToPreviousExercise,
    resetWorkoutState,
    setShowExerciseModal,
    setShowSummaryModal
  };
  
  return (
    <WorkoutContext.Provider value={contextValue}>
      {children}
    </WorkoutContext.Provider>
  );
};

/**
 * Custom hook to access the workout context
 * 
 * @returns {Object} Workout context value
 * @throws {Error} If used outside of WorkoutProvider
 */
export const useWorkout = () => {
  const context = useContext(WorkoutContext);
  
  if (!context) {
    throw new Error('useWorkout must be used within a WorkoutProvider');
  }
  
  return context;
};

export default WorkoutContext;