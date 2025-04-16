import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from 'react-query';
import { Play, Pause, X, Check, AlertTriangle, RefreshCw } from 'lucide-react';

// Components
import ExerciseSelector from '../components/exercise/ExerciseSelector';
import ExerciseCounter from '../components/exercise/ExerciseCounter';
import FeedbackDisplay from '../components/feedback/FeedbackDisplay';
import ExerciseControls from '../components/exercise/ExerciseControls';

// Services
import { startExercise, stopExercise, getExerciseData } from '../services/exerciseService';
import { startVideoFeed, stopVideoFeed } from '../services/videoService';

/**
 * Exercise Tracker page component
 * 
 * This page provides a real-time exercise tracking interface with:
 * - Video feed with pose detection
 * - Exercise selection
 * - Rep counting
 * - Form feedback
 * - Exercise controls (start/stop)
 */
const ExerciseTracker = () => {
  // Video feed reference
  const videoRef = useRef(null);
  
  // Exercise state
  const [selectedExercise, setSelectedExercise] = useState(null);
  const [isTimed, setIsTimed] = useState(false);
  const [targetReps, setTargetReps] = useState(10);
  const [targetDuration, setTargetDuration] = useState(60);
  const [exerciseActive, setExerciseActive] = useState(false);
  const [exerciseCompleted, setExerciseCompleted] = useState(false);
  
  // Result state for completed exercise
  const [exerciseResults, setExerciseResults] = useState(null);
  
  // Get available exercises
  const exercises = [
    { id: 'bicep_curl', name: 'Bicep Curl', isTimed: false },
    { id: 'squat', name: 'Squat', isTimed: false },
    { id: 'pushup', name: 'Push-up', isTimed: false },
    { id: 'lunge', name: 'Lunge', isTimed: false },
    { id: 'plank', name: 'Plank', isTimed: true },
    { id: 'jumping_jack', name: 'Jumping Jack', isTimed: false }
  ];
  
  // Data fetching for active exercise
  const { 
    data: exerciseData,
    refetch: refetchExerciseData
  } = useQuery(
    ['exerciseData'], 
    getExerciseData,
    {
      enabled: exerciseActive,
      refetchInterval: 500, // Poll every 500ms
      onError: (error) => {
        console.error('Failed to fetch exercise data:', error);
      }
    }
  );
  
  // Start exercise mutation
  const startExerciseMutation = useMutation(startExercise, {
    onSuccess: () => {
      setExerciseActive(true);
      setExerciseCompleted(false);
      setExerciseResults(null);
    },
    onError: (error) => {
      console.error('Failed to start exercise:', error);
    }
  });
  
  // Stop exercise mutation
  const stopExerciseMutation = useMutation(stopExercise, {
    onSuccess: (data) => {
      setExerciseActive(false);
      setExerciseCompleted(true);
      setExerciseResults(data);
    },
    onError: (error) => {
      console.error('Failed to stop exercise:', error);
      setExerciseActive(false);
    }
  });
  
  // Initialize video feed
  useEffect(() => {
    let videoFeedUrl = null;
    
    const initVideoFeed = async () => {
      try {
        // Start video feed
        await startVideoFeed();
        
        // Set video source
        if (videoRef.current) {
          videoRef.current.src = `/api/video/feed`;
        }
      } catch (error) {
        console.error('Failed to initialize video feed:', error);
      }
    };
    
    initVideoFeed();
    
    // Cleanup function
    return () => {
      // Stop video feed
      stopVideoFeed().catch(error => {
        console.error('Failed to stop video feed:', error);
      });
      
      // If exercise is active, stop it
      if (exerciseActive) {
        stopExerciseMutation.mutate();
      }
    };
  }, []);
  
  // Handle exercise selection
  const handleExerciseSelect = (exercise) => {
    setSelectedExercise(exercise);
    setIsTimed(exercise.isTimed);
  };
  
  // Handle start exercise
  const handleStartExercise = () => {
    if (!selectedExercise) return;
    
    startExerciseMutation.mutate({
      exercise: selectedExercise.id,
      is_timed: isTimed,
      target_reps: isTimed ? null : targetReps,
      target_duration: isTimed ? targetDuration : null
    });
  };
  
  // Handle stop exercise
  const handleStopExercise = () => {
    stopExerciseMutation.mutate();
  };
  
  // Reset exercise
  const handleResetExercise = () => {
    setSelectedExercise(null);
    setExerciseCompleted(false);
    setExerciseResults(null);
  };
  
  return (
    <div className="flex flex-col h-full space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Exercise Tracker</h1>
      
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Left column - Video feed */}
        <div className="flex flex-col md:col-span-2">
          <div className="relative bg-black rounded-lg overflow-hidden" style={{ minHeight: '400px' }}>
            {/* Video feed */}
            <img 
              ref={videoRef}
              className="w-full h-full object-contain"
              alt="Exercise video feed"
            />
            
            {/* Exercise indicator */}
            {exerciseActive && (
              <div className="absolute top-2 left-2 bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                {selectedExercise?.name} Active
              </div>
            )}
            
            {/* Completed indicator */}
            {exerciseCompleted && (
              <div className="absolute top-2 left-2 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                Exercise Completed
              </div>
            )}
          </div>
          
          {/* Feedback display */}
          {exerciseActive && exerciseData?.feedback && (
            <FeedbackDisplay 
              feedback={exerciseData.feedback} 
              className="mt-4"
            />
          )}
          
          {/* Completed exercise results */}
          {exerciseCompleted && exerciseResults && (
            <div className="mt-4 p-4 bg-white border rounded-lg shadow-sm">
              <h3 className="text-lg font-semibold mb-2">Exercise Summary</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Exercise</p>
                  <p className="font-medium">{exerciseResults.exercise}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Duration</p>
                  <p className="font-medium">{Math.round(exerciseResults.duration)}s</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Repetitions</p>
                  <p className="font-medium">{exerciseResults.rep_count}</p>
                </div>
                {isTimed && (
                  <div>
                    <p className="text-sm text-gray-500">Active Time</p>
                    <p className="font-medium">{Math.round(exerciseResults.time_accumulated)}s</p>
                  </div>
                )}
              </div>
              
              {/* Common feedback */}
              {exerciseResults.statistics?.common_feedback?.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-500 mb-2">Most Common Feedback</h4>
                  <ul className="space-y-1">
                    {exerciseResults.statistics.common_feedback.slice(0, 3).map((item, index) => (
                      <li key={index} className="flex items-start">
                        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 mr-2 flex-shrink-0" />
                        <span className="text-sm">{item.text} ({item.count}x)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={handleResetExercise}
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  New Exercise
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Right column - Controls */}
        <div className="flex flex-col space-y-4">
          {!exerciseActive && !exerciseCompleted ? (
            <>
              {/* Exercise selection */}
              <div className="p-4 bg-white border rounded-lg shadow-sm">
                <h2 className="text-lg font-semibold mb-4">Select Exercise</h2>
                <ExerciseSelector
                  exercises={exercises}
                  selectedExercise={selectedExercise}
                  onSelectExercise={handleExerciseSelect}
                />
                
                {/* Exercise parameters */}
                {selectedExercise && (
                  <div className="mt-4 space-y-4">
                    {isTimed ? (
                      <div>
                        <label htmlFor="targetDuration" className="block text-sm font-medium text-gray-700">
                          Target Duration (seconds)
                        </label>
                        <input
                          type="number"
                          id="targetDuration"
                          value={targetDuration}
                          onChange={(e) => setTargetDuration(Math.max(5, parseInt(e.target.value) || 0))}
                          min="5"
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        />
                      </div>
                    ) : (
                      <div>
                        <label htmlFor="targetReps" className="block text-sm font-medium text-gray-700">
                          Target Repetitions
                        </label>
                        <input
                          type="number"
                          id="targetReps"
                          value={targetReps}
                          onChange={(e) => setTargetReps(Math.max(1, parseInt(e.target.value) || 0))}
                          min="1"
                          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        />
                      </div>
                    )}
                    
                    <button
                      type="button"
                      onClick={handleStartExercise}
                      disabled={!selectedExercise}
                      className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
                    >
                      <Play className="w-5 h-5 mr-2" />
                      Start Exercise
                    </button>
                  </div>
                )}
              </div>
              
              {/* Exercise instructions */}
              {selectedExercise && (
                <div className="p-4 bg-white border rounded-lg shadow-sm">
                  <h2 className="text-lg font-semibold mb-2">{selectedExercise.name} Instructions</h2>
                  <div className="text-sm text-gray-600 space-y-2">
                    {selectedExercise.id === 'bicep_curl' && (
                      <>
                        <p>• Stand with feet shoulder-width apart</p>
                        <p>• Keep elbows close to your torso</p>
                        <p>• Curl weights up to shoulder level</p>
                        <p>• Lower back down with control</p>
                        <p>• Keep your back straight throughout</p>
                      </>
                    )}
                    {selectedExercise.id === 'squat' && (
                      <>
                        <p>• Stand with feet shoulder-width apart</p>
                        <p>• Keep your chest up and back straight</p>
                        <p>• Lower your hips as if sitting in a chair</p>
                        <p>• Knees should track over toes</p>
                        <p>• Return to standing position</p>
                      </>
                    )}
                    {selectedExercise.id === 'pushup' && (
                      <>
                        <p>• Start in plank position with hands shoulder-width apart</p>
                        <p>• Keep your body in a straight line from head to heels</p>
                        <p>• Lower your chest to the floor by bending elbows</p>
                        <p>• Push back up to starting position</p>
                        <p>• Keep elbows at a 45-degree angle from your body</p>
                      </>
                    )}
                    {selectedExercise.id === 'lunge' && (
                      <>
                        <p>• Stand with feet hip-width apart</p>
                        <p>• Step forward with one leg</p>
                        <p>• Lower your hips until both knees are bent at 90 degrees</p>
                        <p>• Keep front knee over ankle, not pushed forward</p>
                        <p>• Push back up to starting position</p>
                      </>
                    )}
                    {selectedExercise.id === 'plank' && (
                      <>
                        <p>• Start in forearm plank position</p>
                        <p>• Keep your body in a straight line from head to heels</p>
                        <p>• Engage your core and glutes</p>
                        <p>• Keep your shoulders over your elbows</p>
                        <p>• Hold the position for the target duration</p>
                      </>
                    )}
                    {selectedExercise.id === 'jumping_jack' && (
                      <>
                        <p>• Stand with feet together and arms at sides</p>
                        <p>• Jump to spread feet and raise arms above head</p>
                        <p>• Jump back to starting position</p>
                        <p>• Maintain a consistent rhythm</p>
                        <p>• Keep movements fluid and controlled</p>
                      </>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Exercise in progress */}
              <div className="p-4 bg-white border rounded-lg shadow-sm">
                <h2 className="text-lg font-semibold mb-4">
                  {selectedExercise?.name} {exerciseActive ? 'in Progress' : 'Completed'}
                </h2>
                
                {/* Counter display */}
                <ExerciseCounter
                  repCount={exerciseData?.rep_count || 0}
                  timeAccumulated={exerciseData?.time_accumulated || 0}
                  isTimed={isTimed}
                  targetReps={targetReps}
                  targetDuration={targetDuration}
                  progress={exerciseData?.progress || 0}
                />
                
                {/* Exercise state */}
                {exerciseActive && exerciseData?.exercise_state && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-gray-500">Current State</p>
                    <p className="text-lg font-semibold">
                      {exerciseData.exercise_state.replace(/_/g, ' ')}
                    </p>
                  </div>
                )}
                
                {/* Controls */}
                <div className="mt-6">
                  {exerciseActive ? (
                    <button
                      type="button"
                      onClick={handleStopExercise}
                      className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                      <X className="w-5 h-5 mr-2" />
                      Stop Exercise
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleResetExercise}
                      className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <RefreshCw className="w-5 h-5 mr-2" />
                      New Exercise
                    </button>
                  )}
                </div>
              </div>
              
              {/* Detailed metrics */}
              {exerciseActive && exerciseData?.detailed_metrics && (
                <div className="p-4 bg-white border rounded-lg shadow-sm">
                  <h3 className="text-md font-semibold mb-2">Detailed Metrics</h3>
                  <div className="space-y-2">
                    {Object.entries(exerciseData.detailed_metrics)
                      .filter(([key]) => !['timed_exercise'].includes(key))
                      .map(([key, value]) => (
                        <div key={key} className="grid grid-cols-2 gap-2">
                          <p className="text-sm text-gray-500">
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </p>
                          <p className="text-sm font-medium text-right">
                            {typeof value === 'number' ? value.toFixed(2) : value}
                          </p>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExerciseTracker;