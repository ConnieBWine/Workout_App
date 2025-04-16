import React from 'react';
import { Dumbbell, Clock } from 'lucide-react';

/**
 * Exercise selection component
 * 
 * This component displays a grid of exercise options that can be selected
 * for tracking, with visual indicators for timed vs. rep-based exercises.
 * 
 * @param {Object} props - Component props
 * @param {Array} props.exercises - List of available exercises with metadata
 * @param {Object} props.selectedExercise - Currently selected exercise
 * @param {Function} props.onSelectExercise - Callback for exercise selection
 */
const ExerciseSelector = ({ exercises, selectedExercise, onSelectExercise }) => {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {exercises.map((exercise) => (
          <button
            key={exercise.id}
            type="button"
            onClick={() => onSelectExercise(exercise)}
            className={`relative flex flex-col items-center p-4 border rounded-md transition-colors ${
              selectedExercise?.id === exercise.id
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500'
                : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
            }`}
          >
            {/* Exercise type indicator */}
            <div className="absolute top-2 right-2">
              {exercise.isTimed ? (
                <Clock className="w-4 h-4 text-gray-500" />
              ) : (
                <Dumbbell className="w-4 h-4 text-gray-500" />
              )}
            </div>
            
            {/* Exercise icon */}
            <div className="flex items-center justify-center w-12 h-12 mb-2 bg-blue-100 rounded-full">
              {exercise.id === 'bicep_curl' && (
                <svg viewBox="0 0 24 24" className="w-6 h-6 text-blue-600" fill="currentColor">
                  <path d="M20.57 14.86L22 13.43 20.57 12 17 15.57 8.43 7 12 3.43 10.57 2 9.14 3.43 7.71 2 5.57 4.14 4.14 2.71 2.71 4.14l1.43 1.43L2 7.71l1.43 1.43L2 10.57 3.43 12 7 8.43 15.57 17 12 20.57 13.43 22l1.43-1.43L16.29 22l2.14-2.14 1.43 1.43 1.43-1.43-1.43-1.43L22 16.29z" />
                </svg>
              )}
              
              {exercise.id === 'squat' && (
                <svg viewBox="0 0 24 24" className="w-6 h-6 text-blue-600" fill="currentColor">
                  <path d="M12 7V6h1V5h-4v1h1v1H9.03a2 2 0 0 0-1.77 1.08C6.33 9.72 5 13.14 5 14.86c0 .75.27 1.64 1.03 2.12.25.16.55.18.84.18h3.99c.89.35 1.75.7 2.87.95 1.48.33 2.33.74 2.33 2.38v.23c0 1.75-.44 3.79-2.06 3.28-.32-.08-.57-.26-.8-.45l-.11-.09c-.12-.11-.22-.32-.22-.69 0-.54.6-1.26 1.12-1.26v-1.5c-1.44 0-2.62 1.46-2.62 2.79 0 .72.25 1.63.96 2.08.35.23.73.36 1.13.36.48 0 .96-.16 1.34-.48 1.09-.9 1.54-2.58 1.54-4.17v-.3c0-2.45-1.53-3.27-3.29-3.68-1-.23-1.97-.6-2.97-.99H8.26c-.38 0-.77-.24-.92-.62C7.12 14.45 8.25 11 9 9.5c.17-.33.59-.5.98-.5h4.04c.33.04.57.19.78.37.36.33.47.27.6.92.1.48 1.5.48 1.6 0 .13-.66.25-.59.6-.92.21-.18.45-.33.78-.37h4.04c.39 0 .8.17.98.5.75 1.5 1.88 4.94 1.66 5.35-.15.39-.54.62-.92.62h-2.05l-.19 1.5h2.35c.29 0 .58-.03.84-.18.77-.48 1.03-1.37 1.03-2.12 0-1.72-1.33-5.14-3.25-6.78A2 2 0 0 0 14.97 7H12z" />
                </svg>
              )}
              
              {exercise.id === 'pushup' && (
                <svg viewBox="0 0 24 24" className="w-6 h-6 text-blue-600" fill="currentColor">
                  <path d="M7 7.5c-.68 0-1.35.19-1.94.53-.58.33-1.09.8-1.45 1.36-.87 1.33-1.79 3.56-1.79 5.29 0 .53.13 1.04.38 1.48.25.44.59.74.99.74.37 0 .71-.25.96-.6.24-.33.42-.76.57-1.12.16-.41.26-.7.55-.87.28-.16.62-.18.91-.18h5.62c.28 0 .54.08.77.4.32.45.82.67 1.42.67.7 0 1.24-.2 1.64-.62.28-.29.45-.69.46-1.12h2.02c.08 0 .15.01.22.03.22.07.36.24.43.45.08.25.13.5.13.78 0 .8-.35 1.5-.92 2.01-.57.49-1.33.79-2.17.79H16c-.04.16-.11.31-.21.44-.27.34-.66.56-1.07.56-.44 0-.86-.27-1.08-.69-.19-.37-.19-.87-.19-1.31h-3c0 .44 0 .94-.19 1.31-.22.42-.64.69-1.08.69-.41 0-.8-.22-1.07-.56-.1-.13-.17-.28-.21-.44H5.77c-.65 0-1.3-.19-1.86-.58-.54-.38-.97-.92-1.18-1.54-.21-.61-.28-1.26-.28-1.88 0-2.01 1.04-4.54 2.09-6.13.51-.78 1.15-1.44 1.9-1.9.75-.47 1.6-.72 2.46-.72h8.21c.58 0 1.16.13 1.71.37.54.25 1.03.59 1.45 1.03.82.88 1.28 1.93 1.63 2.91.33.94.6 1.85.84 2.4.24.55.35.65.4.67.15.07.29.19.38.35.1.17.15.36.15.56 0 .34-.15.64-.37.83-.21.19-.46.26-.7.26h-2.36c-.25 0-.61-.14-.82-.54-.21-.39-.17-.8-.09-1.11.08-.31.18-.57.24-.76.13-.38.24-.72.35-1.09.22-.76.36-1.59.36-2.37 0-.22-.01-.45-.04-.68-.06-.48-.25-.93-.66-1.26-.39-.33-.93-.55-1.56-.55h-2.19c.31.12.54.31.69.55.25.4.32.87.32 1.28 0 .86-.44 1.75-.86 2.52-.39.71-.76 1.35-1.01 1.75l-.1.17H14.1l.12-.25c.11-.22.26-.55.42-.93.2-.49.36-1.05.36-1.53 0-.19-.05-.38-.18-.5-.14-.12-.36-.22-.7-.22-1.05 0-2.33.63-3.47 1.52-1.14.88-2.16 2.01-2.7 3.03-.39.73-.91 1.25-1.5 1.59-.49.28-1 .42-1.46.42z" />
                </svg>
              )}
              
              {exercise.id === 'lunge' && (
                <svg viewBox="0 0 24 24" className="w-6 h-6 text-blue-600" fill="currentColor">
                  <path d="M7 3.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5S9.33 5 8.5 5 7 4.33 7 3.5zM9.34 14l1.41-3.25 1.16 3.47c.21.6.76 1 1.4 1H17v-2h-3.15l-2.09-6.26 1.71-1.7 4.24 4.24 1.41-1.41-4.24-4.24-3.63-1.3a1.49 1.49 0 0 0-1.75.55L6.64 7.75l-1.69.22L2.46 12h2.03l1.7-2.4L7.36 21h2.02l-1.05-7h.91s.04.08.05.12z" />
                </svg>
              )}
              
              {exercise.id === 'plank' && (
                <svg viewBox="0 0 24 24" className="w-6 h-6 text-blue-600" fill="currentColor">
                  <path d="M19 12a2 2 0 1 0-2-2c0 1.11.89 2 2 2m-7 0a2 2 0 1 0-2-2c0 1.11.89 2 2 2m-7 0a2 2 0 1 0-2-2c0 1.11.89 2 2 2m0-5a2 2 0 1 0-2-2c0 1.11.89 2 2 2m7 0a2 2 0 1 0-2-2c0 1.11.89 2 2 2m7 0a2 2 0 1 0-2-2c0 1.11.89 2 2 2m-7 10a2 2 0 1 0-2-2c0 1.11.89 2 2 2m-7 0a2 2 0 1 0-2-2c0 1.11.89 2 2 2m14 0a2 2 0 1 0-2-2c0 1.11.89 2 2 2z" />
                </svg>
              )}
              
              {exercise.id === 'jumping_jack' && (
                <svg viewBox="0 0 24 24" className="w-6 h-6 text-blue-600" fill="currentColor">
                  <path d="M13.5 5.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5S11.17 4 12 4s1.5.67 1.5 1.5zM20 12v-1h-1.76c-.55-3.95-3.54-7-7.24-7-3.7 0-6.69 3.05-7.24 7H2v2h1.76c.55 3.95 3.54 7 7.24 7 3.7 0 6.69-3.05 7.24-7H22v-1h-2zm-8-5.59c2.31 0 4.32 1.46 5.1 3.59h-2.43l-1.72-1.97L10 7.17 10.38 8H8.38c.8-1.15 2.18-1.59 3.62-1.59zm0 11.18c-2.31 0-4.18-1.46-4.96-3.59h2.29l1.72 1.97 2.95.84-.38-.84h2.38c-.8 1.15-2.19 1.62-4 1.62z" />
                </svg>
              )}
            </div>
            
            {/* Exercise name */}
            <span className="text-sm font-medium">{exercise.name}</span>
            
            {/* Exercise type label */}
            <span className="mt-1 text-xs text-gray-500">
              {exercise.isTimed ? 'Timed' : 'Repetition'}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ExerciseSelector;