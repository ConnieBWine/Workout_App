import React, { useEffect, useRef } from 'react';
import { Clock, RotateCw } from 'lucide-react';

/**
 * Exercise counter component for displaying rep counts or elapsed time
 * 
 * This component renders either a repetition counter or a time counter
 * based on the exercise type, along with a progress indicator. It includes
 * visual feedback to show progress toward the target goal.
 * 
 * @param {Object} props - Component props
 * @param {number} props.repCount - Current repetition count
 * @param {number} props.timeAccumulated - Accumulated exercise time in seconds
 * @param {boolean} props.isTimed - Whether this is a timed exercise
 * @param {number} props.targetReps - Target repetition count
 * @param {number} props.targetDuration - Target duration in seconds
 * @param {number} props.progress - Progress percentage (0-100)
 */
const ExerciseCounter = ({ 
  repCount, 
  timeAccumulated, 
  isTimed, 
  targetReps,
  targetDuration,
  progress 
}) => {
  // References for animation
  const progressCircleRef = useRef(null);
  
  // Format time display (MM:SS)
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Update progress circle animation
  useEffect(() => {
    if (progressCircleRef.current) {
      const circumference = 2 * Math.PI * 45; // SVG circle radius is 45
      const offset = circumference - (progress / 100) * circumference;
      progressCircleRef.current.style.strokeDashoffset = offset;
    }
  }, [progress]);

  return (
    <div className="flex flex-col items-center">
      {/* SVG Progress Circle */}
      <div className="relative w-48 h-48">
        {/* Background circle */}
        <svg className="w-full h-full" viewBox="0 0 100 100">
          <circle
            className="text-gray-200"
            strokeWidth="5"
            stroke="currentColor"
            fill="transparent"
            r="45"
            cx="50"
            cy="50"
          />
          {/* Progress circle */}
          <circle
            ref={progressCircleRef}
            className="text-blue-600 transition-all duration-300 ease-in-out"
            strokeWidth="5"
            strokeDasharray={2 * Math.PI * 45}
            strokeDashoffset={2 * Math.PI * 45} // Initial offset (empty)
            strokeLinecap="round"
            stroke="currentColor"
            fill="transparent"
            r="45"
            cx="50"
            cy="50"
            transform="rotate(-90 50 50)"
          />
        </svg>

        {/* Counter display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {isTimed ? (
            <>
              <Clock className="w-6 h-6 text-blue-600 mb-1" />
              <div className="text-3xl font-bold text-gray-900">
                {formatTime(timeAccumulated)}
              </div>
              <div className="text-sm text-gray-500 mt-1">
                Target: {formatTime(targetDuration)}
              </div>
            </>
          ) : (
            <>
              <RotateCw className="w-6 h-6 text-blue-600 mb-1" />
              <div className="text-3xl font-bold text-gray-900">
                {repCount}
              </div>
              <div className="text-sm text-gray-500 mt-1">
                Target: {targetReps}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Percentage display */}
      <div className="mt-4 text-lg font-semibold text-gray-700">
        {Math.round(progress)}% Complete
      </div>
    </div>
  );
};

export default ExerciseCounter;